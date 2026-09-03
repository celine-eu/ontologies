"""Tests for MappingEngine."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from celine.mapper.engine import MappingEngine, MappingError
from celine.mapper.spec import MappingSpecLoader

SPECS_DIR = Path(__file__).resolve().parents[2] / "src" / "celine" / "mapper" / "specs"
FIXTURES_DIR = Path(__file__).parent / "fixtures"

_loader = MappingSpecLoader()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _engine(spec_file: str, context: dict | None = None) -> MappingEngine:
    spec = _loader.load(SPECS_DIR / spec_file)
    return MappingEngine(spec=spec, context=context or {})


def _fixture(name: str) -> list[dict] | dict:
    with (FIXTURES_DIR / name).open() as fh:
        return json.load(fh)


# ---------------------------------------------------------------------------
# kind=literal
# ---------------------------------------------------------------------------

def test_literal_string_field() -> None:
    eng = _engine("rec_community.yaml")
    row = {"key": "it-folgaria", "name": "REC Folgaria", "description": "A REC."}
    node = eng.map_one(row)
    assert node["dct:identifier"] == "it-folgaria"
    assert node["rdfs:label"] == "REC Folgaria"


def test_literal_decimal_coercion() -> None:
    eng = _engine("obs_rec_energy.yaml")
    row = {
        "ts": "2024-06-01T00:00:00+00:00",
        "rec_id": "it-folgaria",
        "substation_id": "cp-0421",
        "total_consumption_kwh": "12.5",
        "total_production_kwh": "8.3",
        "self_consumption_kwh": "7.1",
        "self_consumption_ratio": "0.856",
    }
    node = eng.map_one(row)
    assert node["sosa:hasSimpleResult"] == 7.1
    assert isinstance(node["rdf:value"], float)


def test_literal_none_skipped() -> None:
    eng = _engine("rec_community.yaml")
    row = {"key": "it-folgaria", "name": None}
    node = eng.map_one(row)
    assert "rdfs:label" not in node


# ---------------------------------------------------------------------------
# kind=iri
# ---------------------------------------------------------------------------

def test_iri_produces_at_id() -> None:
    eng = _engine("obs_meter_energy.yaml")
    row = {
        "_id": "row-001",
        "device_id": "dev-001",
        "ts": "2024-06-01T00:00:00+00:00",
        "consumption_kw": 1.2,
        "production_kw": 0.8,
        "self_consumed_kw": 0.7,
    }
    node = eng.map_one(row)
    sensor = node["sosa:madeBySensor"]
    assert isinstance(sensor, dict)
    # The engine's default base, applied to a now-relative `iri_template`.
    # Before 2026-09-03 no base was applied to `iri_template` at all and this
    # asserted `https://w3id.org/celine/device/dev-001`, an IRI that 404s.
    assert sensor["@id"] == "http://api.celine.localhost/entities/device/dev-001"


# ---------------------------------------------------------------------------
# kind=nested
# ---------------------------------------------------------------------------

def test_nested_creates_subnode() -> None:
    eng = _engine("rec_member.yaml", context={"community_key": "it-folgaria"})
    row = _fixture("member_detail.json")
    node = eng.map_one(row)
    dp = node.get("peco:has_port")
    assert dp is not None
    # Single item → dict, not list
    if isinstance(dp, list):
        dp = dp[0]
    assert dp["@type"] == "peco:Electric_POD"
    assert dp["dct:identifier"] == "dp-001"


def test_nested_list_multiple_items() -> None:
    eng = _engine("rec_community.yaml")
    row = _fixture("community_detail.json")
    node = eng.map_one(row)
    contained = node.get("peco:contains")
    assert contained is not None
    items = contained if isinstance(contained, list) else [contained]
    assert len(items) == 2  # two topology nodes in fixture


# ---------------------------------------------------------------------------
# kind=constant
# ---------------------------------------------------------------------------

def test_constant_injected() -> None:
    eng = _engine("obs_rec_energy.yaml")
    row = {
        "ts": "2024-06-01T00:00:00+00:00",
        "rec_id": "it-folgaria",
        "substation_id": "cp-0421",
        "total_consumption_kwh": 10.0,
        "total_production_kwh": 8.0,
        "self_consumption_kwh": 7.0,
        "self_consumption_ratio": 0.875,
    }
    node = eng.map_one(row)
    assert node["sosa:observedProperty"] == "https://w3id.org/celine/property/self-consumption-kwh"


# ---------------------------------------------------------------------------
# @id generation
# ---------------------------------------------------------------------------

def test_id_uses_context_var() -> None:
    """Moved off obs_rec_energy, which no longer takes one: its rows carry
    `rec_id` and `substation_id` of their own, so pulling the community from the
    caller's context was both unnecessary and a way for the two to disagree.
    obs_pv_forecast still keys on a context variable, so it covers the feature."""
    eng = _engine("obs_pv_forecast.yaml", context={"community_key": "it-folgaria"})
    row = {"forecast_time_utc": "2024-06-01T00:00:00+00:00", "run_time_utc": "2024-06-01T00:00:00+00:00",
           "provider": "acme", "pv_kwh_per_kwp_hourly": 0.4}
    node = eng.map_one(row)
    assert "it-folgaria" in node["@id"]
    assert "2024-06-01" in node["@id"]


def test_id_uses_row_columns_for_the_models_full_grain() -> None:
    """obs_rec_energy is grouped by (ts, rec_id, substation_id). An @id built
    from fewer of those mints one IRI for several distinct rows."""
    eng = _engine("obs_rec_energy.yaml")
    base = {"ts": "2024-06-01T00:00:00+00:00", "rec_id": "it-folgaria",
            "self_consumption_kwh": 7.0, "total_consumption_kwh": 10.0,
            "total_production_kwh": 8.0, "self_consumption_ratio": 0.7}
    a = eng.map_one({**base, "substation_id": "cp-0421"})
    b = eng.map_one({**base, "substation_id": "cp-0422"})
    assert a["@id"] != b["@id"]


def test_type_set_from_spec() -> None:
    eng = _engine("rec_community.yaml")
    row = {"key": "x", "name": "Test"}
    node = eng.map_one(row)
    assert node["@type"] == "peco:Renewable_energy_community"


# ---------------------------------------------------------------------------
# Required field errors
# ---------------------------------------------------------------------------

def test_required_field_raises() -> None:
    eng = _engine("obs_meter_energy.yaml")
    row = {"ts": "2024-06-01T00:00:00+00:00", "consumption_kw": 1.0}  # missing device_id
    with pytest.raises(MappingError) as exc_info:
        eng.map_one(row)
    assert "device_id" in str(exc_info.value)


def test_required_field_empty_string_raises() -> None:
    eng = _engine("obs_meter_energy.yaml")
    row = {"ts": "2024-06-01T00:00:00+00:00", "device_id": "", "consumption_kw": 1.0}
    with pytest.raises(MappingError):
        eng.map_one(row)


# ---------------------------------------------------------------------------
# map_many
# ---------------------------------------------------------------------------

def test_map_many_energy_rows() -> None:
    eng = _engine("obs_rec_energy.yaml", context={"community_key": "it-folgaria"})
    rows = _fixture("rec_energy_rows.json")
    nodes = eng.map_many(rows)
    assert len(nodes) == 3
    assert all(n["@type"] == "sosa:Observation" for n in nodes)
    assert all("@id" in n for n in nodes)


def test_map_many_meter_rows() -> None:
    eng = _engine("obs_meter_energy.yaml")
    rows = _fixture("meter_data_rows.json")
    nodes = eng.map_many(rows)
    assert len(nodes) == 2


def test_map_many_pv_forecast() -> None:
    eng = _engine("obs_pv_forecast.yaml", context={"community_key": "it-folgaria"})
    rows = _fixture("pv_forecast_rows.json")
    nodes = eng.map_many(rows)
    assert len(nodes) == 2
    assert all(n["@type"] == "peco:Forecast" for n in nodes)


# ---------------------------------------------------------------------------
# Template dialects — spec format version selects the renderer
# ---------------------------------------------------------------------------

def _inline(body: str, context: dict | None = None, **engine_kw) -> MappingEngine:
    """Build an engine from an inline spec, schema-validated like a real one."""
    return MappingEngine(
        spec=_loader.load_from_string(body),
        context=context or {},
        **engine_kw,
    )


_V1 = '''
version: "1"
target_type: "sosa:Observation"
id_template: "obs/{device_id}"
fields: []
'''

_V2 = '''
version: "2"
target_type: "sosa:Observation"
id_template: "obs/{{ device_id }}"
fields: []
'''


def test_v1_templates_still_render_with_single_braces() -> None:
    """The old dialect is not deprecated and not sniffed for.

    Specs in celine-pipelines and digital-twin declare version "1" and this
    package cannot see them; a migration that broke them would fail somewhere
    else entirely, with nothing here to catch it.
    """
    node = _inline(_V1).map_one({"device_id": "dev-001"})
    assert node["@id"].endswith("/obs/dev-001")


def test_v1_leaves_jinja_syntax_alone() -> None:
    """A `{{ x }}` in a version "1" spec is literal text, not a template.

    Proves the dialect comes from `version` and never from the template's
    content — the whole reason for gating on a declared field.
    """
    spec = _V1.replace('id_template: "obs/{device_id}"', 'id_template: "obs/{{ device_id }}"')
    node = _inline(spec).map_one({"device_id": "dev-001"})
    # `str.format_map` collapses `{{`/`}}` to literal braces and substitutes
    # nothing — the inner text, spaces included, survives verbatim.
    assert node["@id"].endswith("/obs/{ device_id }")


def test_v2_renders_jinja() -> None:
    node = _inline(_V2).map_one({"device_id": "dev-001"})
    assert node["@id"].endswith("/obs/dev-001")


def test_v2_supports_filters_and_conditionals() -> None:
    """The expressiveness the migration was for.

    A branch on a column is what five specs could not express, which is how they
    ended up pointing `sosa:observedProperty` at a constant instead.
    """
    spec = _V2.replace(
        'id_template: "obs/{{ device_id }}"',
        'id_template: "obs/{% if kind == \'import\' %}in{% else %}out{% endif %}/{{ device_id | lower }}"',
    )
    eng = _inline(spec)
    assert eng.map_one({"device_id": "DEV-1", "kind": "import"})["@id"].endswith("/obs/in/dev-1")
    assert eng.map_one({"device_id": "DEV-1", "kind": "export"})["@id"].endswith("/obs/out/dev-1")


def test_v2_unknown_variable_raises_and_names_it() -> None:
    """StrictUndefined, and the reason the whole change is worth making.

    Jinja's default `Undefined` renders the empty string, which would have turned
    a typo'd column into a silently truncated IRI — indistinguishable from a
    correct one, and collapsing distinct rows onto a single subject. v1 raised
    here; v2 must not be a regression.
    """
    with pytest.raises(MappingError) as exc:
        _inline(_V2).map_one({"wrong_column": "dev-001"})
    assert "device_id" in str(exc.value)


def test_v2_sandbox_refuses_attribute_escape() -> None:
    """A `spec_file` template comes from another repository's working tree.

    This is the miniature of the pluggable-Python-module idea that was declined:
    a template is data, and must not reach the interpreter.
    """
    spec = _V2.replace('id_template: "obs/{{ device_id }}"', 'id_template: "{{ device_id.__class__.__mro__ }}"')
    with pytest.raises(MappingError):
        _inline(spec).map_one({"device_id": "dev-001"})


# ---------------------------------------------------------------------------
# base_uri — applied to id_template *and* iri_template
# ---------------------------------------------------------------------------

_V2_IRI = '''
version: "2"
target_type: "sosa:Observation"
id_template: "obs/{{ device_id }}"
fields:
  - source: device_id
    target: "sosa:madeBySensor"
    kind: iri
    iri_template: "device/{{ value }}"
  - target: "sosa:observedProperty"
    kind: constant
    value: "https://w3id.org/celine/property/meter-consumption-kwh"
'''


def test_base_uri_reaches_both_id_and_iri_templates() -> None:
    """Changing the setting changes the emitted IRIs — both kinds of them.

    Until 2026-09-03 `base_uri` was dead code (it applied only to a relative
    `id_template`, and every packaged spec was absolute) and `iri_template` never
    had a base applied at all. A spec whose subject moved while its object
    references did not would emit a graph whose two halves disagree about where
    its entities live, so both are asserted together on purpose.
    """
    node = _inline(_V2_IRI, base_uri="https://datasets.example.test/").map_one(
        {"device_id": "dev-001"}
    )
    assert node["@id"] == "https://datasets.example.test/obs/dev-001"
    assert node["sosa:madeBySensor"]["@id"] == "https://datasets.example.test/device/dev-001"


def test_constants_are_not_rebased() -> None:
    """A constant names an ontology *term*, not an entity this mapping mints.

    Terms belong to whoever publishes the vocabulary. Rebasing them would rewrite
    every property IRI in the graph the first time a deployment set its own base.
    """
    node = _inline(_V2_IRI, base_uri="https://datasets.example.test/").map_one(
        {"device_id": "dev-001"}
    )
    assert node["sosa:observedProperty"] == (
        "https://w3id.org/celine/property/meter-consumption-kwh"
    )


def test_absolute_templates_are_left_alone() -> None:
    """Back-compat for any spec that has not migrated its templates."""
    spec = _V2.replace('id_template: "obs/{{ device_id }}"', 'id_template: "https://elsewhere.test/obs/{{ device_id }}"')
    node = _inline(spec, base_uri="https://datasets.example.test/").map_one({"device_id": "dev-001"})
    assert node["@id"] == "https://elsewhere.test/obs/dev-001"


def test_unknown_format_version_is_refused() -> None:
    """The schema rejects it first; this pins the engine's own guard.

    Reached when a consumer builds a MappingSpec directly rather than through the
    loader — which `dataset-api` does with a stored JSON column.
    """
    from celine.mapper.spec import MappingSpec

    spec = MappingSpec(version="99", target_type="sosa:Observation", id_template="x", fields=())
    with pytest.raises(MappingError) as exc:
        MappingEngine(spec=spec)
    assert "99" in str(exc.value)
