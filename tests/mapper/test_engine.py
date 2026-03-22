"""Tests for MappingEngine."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from celine.mapper.engine import MappingEngine, MappingError
from celine.mapper.spec import MappingSpecLoader

SPECS_DIR = Path(__file__).resolve().parent.parent.parent / "celine" / "mapper" / "specs"
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
    eng = _engine("obs_rec_energy.yaml", context={"community_key": "it-folgaria"})
    row = {
        "ts": "2024-06-01T00:00:00+00:00",
        "total_consumption_kw": "12.5",
        "total_production_kw": "8.3",
        "self_consumption_kw": "7.1",
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
    assert sensor["@id"] == "https://w3id.org/celine/device/dev-001"


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
    eng = _engine("obs_rec_energy.yaml", context={"community_key": "it-folgaria"})
    row = {
        "ts": "2024-06-01T00:00:00+00:00",
        "total_consumption_kw": 10.0,
        "total_production_kw": 8.0,
        "self_consumption_kw": 7.0,
        "self_consumption_ratio": 0.875,
    }
    node = eng.map_one(row)
    assert node["sosa:observedProperty"] == "https://w3id.org/celine/property/self-consumption-kw"


# ---------------------------------------------------------------------------
# @id generation
# ---------------------------------------------------------------------------

def test_id_uses_context_var() -> None:
    eng = _engine("obs_rec_energy.yaml", context={"community_key": "it-folgaria"})
    row = {"ts": "2024-06-01T00:00:00+00:00", "self_consumption_kw": 7.0,
           "total_consumption_kw": 10.0, "total_production_kw": 8.0,
           "self_consumption_ratio": 0.7}
    node = eng.map_one(row)
    assert "it-folgaria" in node["@id"]
    assert "2024-06-01" in node["@id"]


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
