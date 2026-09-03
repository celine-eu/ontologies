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


# One row in the shape of the `*_measurements_*` gold views: one quantity, one
# observed property, one surrogate that already encodes the grain. The wide-row
# fixtures this replaced put three or four quantities on one sosa:Observation,
# which SSN forbids.
_MEASUREMENT = {
    "observation_id": "55740661d9a41d0dc81ab810d23cb3b1",
    "result_time": "2024-06-01T00:00:00+00:00",
    "observed_property": "https://w3id.org/celine-eu#GridImportEnergy",
    "value": "12.5",
    "unit": "http://qudt.org/vocab/unit/KiloW-HR",
    "feature_iri": "https://w3id.org/celine-eu/id/sharing-group/it-folgaria/cp-0421",
    "sensor_iri": "https://w3id.org/celine-eu/id/device/dev-001",
}


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
    eng = _engine("obs_energy_measurement.yaml")
    node = eng.map_one(_MEASUREMENT)
    assert node["sosa:hasSimpleResult"] == 12.5
    assert isinstance(node["sosa:hasSimpleResult"], float)


def test_literal_none_skipped() -> None:
    eng = _engine("rec_community.yaml")
    row = {"key": "it-folgaria", "name": None}
    node = eng.map_one(row)
    assert "rdfs:label" not in node


# ---------------------------------------------------------------------------
# kind=iri
# ---------------------------------------------------------------------------

def test_iri_produces_at_id() -> None:
    """Through an `iri_template`, which is what applies the base.

    Rehomed twice: off obs_meter_energy when that spec was deleted, then off
    obs_meter_forecast when v0.11 removed its `sosa:madeBySensor` — no sensor makes
    a forecast, an algorithm does, so that field became `sosa:usedProcedure` on an
    IRI the pipeline supplies. rec_asset still renders a template.
    """
    eng = _engine("rec_asset.yaml", context={"community_key": "it-folgaria"})
    node = eng.map_one({"key": "pv-001", "name": "Roof array", "sensor_id": "dev-001"})
    assert node["sosa:isHostedBy"]["@id"].endswith("/sensor/dev-001")


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
    """From an inline spec, because no packaged spec carries a constant any more.

    That is the point rather than an inconvenience: every `kind: constant` in this
    directory was a `sosa:observedProperty` pointing at a
    `https://w3id.org/celine/property/…` IRI in no namespace, and v0.11 replaced the
    last three with a column the pipeline fills. The feature still works and is
    still tested; nothing in the shipped specs needs it.
    """
    spec = _V2.replace(
        "fields: []",
        'fields:\n'
        '  - target: "sosa:observedProperty"\n'
        '    kind: constant\n'
        '    value: "https://w3id.org/celine-eu#GridImportEnergy"',
    )
    node = _inline(spec).map_one({"device_id": "dev-001"})
    # Not rebased: a constant names an ontology term, not an entity this spec mints.
    assert node["sosa:observedProperty"] == "https://w3id.org/celine-eu#GridImportEnergy"


# ---------------------------------------------------------------------------
# @id generation
# ---------------------------------------------------------------------------

def test_context_var_reaches_a_template() -> None:
    """Caller context still reaches templates — but no longer any `id_template`.

    Every packaged spec now keys its `@id` on row columns alone. That is a
    correction, not an accident: obs_rec_energy took the community from the caller
    while its rows carried `rec_id`, which is how the two get to disagree, and the
    v0.11 forecast rewrite removed the last of them. rec_asset still projects
    `community_key` into an `iri_template`, which is what this covers.
    """
    eng = _engine("rec_asset.yaml", context={"community_key": "it-folgaria"})
    node = eng.map_one({"key": "pv-001", "name": "Roof array"})
    assert node["celine:usesAsset"]["@id"].endswith("/context/it-folgaria")


def test_id_uses_the_surrogate_that_carries_the_grain() -> None:
    """The grain moved into the view, and this pins that it is still honoured.

    obs_rec_energy built its @id from (ts, rec_id, substation_id) directly, and
    dropping any one of them minted a single IRI for distinct rows — the defect
    recorded against digital-twin\'s copy. obs_energy_measurement instead keys on
    `observation_id`, an md5 the view computes over its own full grain, which is
    what lets one id_template serve three source tables whose grains differ. Two
    rows that differ only in the surrogate must still land on different IRIs.
    """
    eng = _engine("obs_energy_measurement.yaml")
    a = eng.map_one({**_MEASUREMENT, "observation_id": "aaa"})
    b = eng.map_one({**_MEASUREMENT, "observation_id": "bbb"})
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
    """A required *field*, not a template variable — those fail earlier, in the
    renderer, and would prove something else."""
    eng = _engine("obs_energy_measurement.yaml")
    row = {k: v for k, v in _MEASUREMENT.items() if k != "observed_property"}
    with pytest.raises(MappingError) as exc_info:
        eng.map_one(row)
    assert "observed_property" in str(exc_info.value)


def test_required_field_empty_string_raises() -> None:
    eng = _engine("obs_energy_measurement.yaml")
    with pytest.raises(MappingError):
        eng.map_one({**_MEASUREMENT, "observed_property": ""})


# ---------------------------------------------------------------------------
# map_many
# ---------------------------------------------------------------------------

def test_map_many_energy_rows() -> None:
    eng = _engine("obs_energy_measurement.yaml")
    rows = _fixture("rec_measurement_rows.json")
    nodes = eng.map_many(rows)
    # Three intervals x four quantities. One quantity per Observation is the
    # whole reason this spec superseded the wide-row one.
    assert len(nodes) == 12
    assert all(n["@type"] == "sosa:Observation" for n in nodes)
    assert all("@id" in n for n in nodes)


def test_map_many_meter_rows() -> None:
    eng = _engine("obs_energy_measurement.yaml")
    rows = _fixture("meter_measurement_rows.json")
    nodes = eng.map_many(rows)
    # Two intervals x three quantities.
    assert len(nodes) == 6


def test_map_many_pv_forecast() -> None:
    eng = _engine("obs_pv_forecast.yaml")
    rows = _fixture("pv_forecast_rows.json")
    nodes = eng.map_many(rows)
    assert len(nodes) == 2
    # celine:Forecast, not peco:Forecast — v0.11. The type is declared rather than
    # left to OWL-RL to infer from a sosa: property on a peco: class.
    assert all(n["@type"] == "celine:Forecast" for n in nodes)
    # A forecast is about a later instant than the one it was made at. Conflating
    # the two was the previous spec's defect, so it is asserted rather than assumed.
    assert all(n["celine:forecastTargetTime"] > n["sosa:resultTime"] for n in nodes)


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
