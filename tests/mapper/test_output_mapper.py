"""Tests for OutputMapper adapter."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from celine.mapper.output_mapper import OutputMapper

SPECS_DIR = Path(__file__).resolve().parent.parent.parent / "celine" / "mapper" / "specs"
FIXTURES_DIR = Path(__file__).parent / "fixtures"


def _fixture(name: str) -> list[dict] | dict:
    with (FIXTURES_DIR / name).open() as fh:
        return json.load(fh)


# ---------------------------------------------------------------------------
# Construction
# ---------------------------------------------------------------------------

def test_from_yaml_path() -> None:
    mapper = OutputMapper.from_yaml_path(SPECS_DIR / "obs_rec_energy.yaml",
                                         context={"community_key": "x"})
    assert mapper is not None


# ---------------------------------------------------------------------------
# .map() — single row contract (digital-twin executor interface)
# ---------------------------------------------------------------------------

def test_map_returns_dict() -> None:
    mapper = OutputMapper.from_yaml_path(SPECS_DIR / "obs_rec_energy.yaml",
                                         context={"community_key": "it-folgaria"})
    rows = _fixture("rec_energy_rows.json")
    result = mapper.map(rows[0])
    assert isinstance(result, dict)
    assert "@id" in result
    assert "@type" in result


def test_map_type_correct() -> None:
    mapper = OutputMapper.from_yaml_path(SPECS_DIR / "obs_rec_energy.yaml",
                                         context={"community_key": "it-folgaria"})
    row = _fixture("rec_energy_rows.json")[0]
    result = mapper.map(row)
    assert result["@type"] == "sosa:Observation"


def test_map_meter_row() -> None:
    mapper = OutputMapper.from_yaml_path(SPECS_DIR / "obs_meter_energy.yaml")
    row = _fixture("meter_data_rows.json")[0]
    result = mapper.map(row)
    assert result["@type"] == "sosa:Observation"
    assert result["sosa:madeBySensor"]["@id"].endswith("device-meter-alice-001")


def test_map_community() -> None:
    mapper = OutputMapper.from_yaml_path(SPECS_DIR / "rec_community.yaml")
    row = _fixture("community_detail.json")
    result = mapper.map(row)
    assert result["@type"] == "peco:Renewable_energy_community"
    assert result["dct:identifier"] == "it-folgaria"


def test_map_member_with_delivery_points() -> None:
    mapper = OutputMapper.from_yaml_path(SPECS_DIR / "rec_member.yaml",
                                         context={"community_key": "it-folgaria"})
    row = _fixture("member_detail.json")
    result = mapper.map(row)
    assert result["@type"] == "peco:Energy_community_member"
    dp = result.get("peco:has_port")
    assert dp is not None


def test_map_asset() -> None:
    mapper = OutputMapper.from_yaml_path(SPECS_DIR / "rec_asset.yaml",
                                         context={"community_key": "it-folgaria"})
    row = _fixture("asset_detail.json")
    result = mapper.map(row)
    assert result["@type"] == "saref:Device"
    sensor_link = result.get("sosa:isHostedBy")
    assert sensor_link is not None
    assert "sensor-pv-alice-001" in sensor_link["@id"]


# ---------------------------------------------------------------------------
# .map_many() — batch variant
# ---------------------------------------------------------------------------

def test_map_many_returns_list() -> None:
    mapper = OutputMapper.from_yaml_path(SPECS_DIR / "obs_rec_energy.yaml",
                                         context={"community_key": "it-folgaria"})
    rows = _fixture("rec_energy_rows.json")
    results = mapper.map_many(rows)
    assert len(results) == len(rows)
    assert all(isinstance(r, dict) for r in results)


def test_map_many_unique_ids() -> None:
    """Each row must produce a unique @id."""
    mapper = OutputMapper.from_yaml_path(SPECS_DIR / "obs_rec_energy.yaml",
                                         context={"community_key": "it-folgaria"})
    rows = _fixture("rec_energy_rows.json")
    ids = [mapper.map(r)["@id"] for r in rows]
    assert len(set(ids)) == len(ids)


# ---------------------------------------------------------------------------
# Simulated digital-twin executor pattern
# ---------------------------------------------------------------------------

def test_executor_pattern() -> None:
    """Mimic how the DT executor uses output_mapper: [output_mapper.map(item) for item in items]."""
    mapper = OutputMapper.from_yaml_path(SPECS_DIR / "obs_meter_energy.yaml")
    raw_items = _fixture("meter_data_rows.json")

    mapped_items = [mapper.map(item) for item in raw_items]

    assert len(mapped_items) == 2
    for item in mapped_items:
        assert "@id" in item
        assert "@type" in item
        assert item["@type"] == "sosa:Observation"
