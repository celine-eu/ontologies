"""Tests for CelineGraphBuilder and SHACL validation."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from celine.mapper.engine import MappingEngine
from celine.mapper.graph import CelineGraphBuilder, SHACLResult
from celine.mapper.spec import MappingSpecLoader

SPECS_DIR = Path(__file__).resolve().parent.parent.parent / "celine" / "mapper" / "specs"
FIXTURES_DIR = Path(__file__).parent / "fixtures"

_loader = MappingSpecLoader()


def _nodes(spec_file: str, fixture_file: str, context: dict | None = None) -> list[dict]:
    spec = _loader.load(SPECS_DIR / spec_file)
    engine = MappingEngine(spec=spec, context=context or {})
    with (FIXTURES_DIR / fixture_file).open() as fh:
        data = json.load(fh)
    rows = data if isinstance(data, list) else [data]
    return engine.map_many(rows)


# ---------------------------------------------------------------------------
# build_document
# ---------------------------------------------------------------------------

def test_build_document_structure() -> None:
    builder = CelineGraphBuilder()
    nodes = _nodes("obs_rec_energy.yaml", "rec_energy_rows.json", {"community_key": "it-folgaria"})
    doc = builder.build_document(nodes)
    assert "@context" in doc
    assert "@graph" in doc
    assert isinstance(doc["@graph"], list)
    assert len(doc["@graph"]) == 3


def test_build_document_context_has_celine_prefix() -> None:
    builder = CelineGraphBuilder()
    nodes = _nodes("obs_rec_energy.yaml", "rec_energy_rows.json", {"community_key": "x"})
    doc = builder.build_document(nodes)
    ctx = doc["@context"]
    assert "celine" in ctx
    assert "peco" in ctx
    assert "sosa" in ctx


# ---------------------------------------------------------------------------
# validate_json_schema
# ---------------------------------------------------------------------------

def test_json_schema_valid_document() -> None:
    """A document with @id and @type on all nodes should pass."""
    builder = CelineGraphBuilder()
    nodes = _nodes("obs_rec_energy.yaml", "rec_energy_rows.json", {"community_key": "x"})
    doc = builder.build_document(nodes)
    builder.validate_json_schema(doc)  # must not raise


def test_json_schema_missing_at_graph_raises() -> None:
    import jsonschema  # noqa: PLC0415

    builder = CelineGraphBuilder()
    with pytest.raises(jsonschema.ValidationError):
        builder.validate_json_schema({"@context": {}})  # missing @graph


def test_json_schema_empty_graph_raises() -> None:
    import jsonschema  # noqa: PLC0415

    builder = CelineGraphBuilder()
    with pytest.raises(jsonschema.ValidationError):
        builder.validate_json_schema({"@context": {}, "@graph": []})


# ---------------------------------------------------------------------------
# to_rdf_graph
# ---------------------------------------------------------------------------

def test_to_rdf_graph_parses() -> None:
    import rdflib  # noqa: PLC0415

    builder = CelineGraphBuilder()
    nodes = _nodes("obs_rec_energy.yaml", "rec_energy_rows.json", {"community_key": "x"})
    doc = builder.build_document(nodes)
    g = builder.to_rdf_graph(doc)
    assert isinstance(g, rdflib.Graph)
    assert len(g) > 0


# ---------------------------------------------------------------------------
# validate_shacl
# ---------------------------------------------------------------------------

def test_shacl_valid_rec_energy_observations() -> None:
    """sosa:Observation nodes have @id and @type, so they conform as NodeBase."""
    builder = CelineGraphBuilder()
    nodes = _nodes("obs_rec_energy.yaml", "rec_energy_rows.json", {"community_key": "it-folgaria"})
    doc = builder.build_document(nodes)
    g = builder.to_rdf_graph(doc)
    result = builder.validate_shacl(g)
    assert isinstance(result, SHACLResult)
    # SHACL shapes are defined only for CELINE core classes; SOSA Observation
    # has no SHACL shape in celine.shacl.ttl — it should report conforms=True.
    assert result.conforms is True


def test_shacl_result_str_conforms() -> None:
    r = SHACLResult(conforms=True)
    assert "conforms" in str(r)


def test_shacl_result_str_violations() -> None:
    r = SHACLResult(conforms=False, violations=["Violation A", "Violation B"])
    s = str(r)
    assert "NOT conform" in s
    assert "Violation A" in s


# ---------------------------------------------------------------------------
# validate_full pipeline
# ---------------------------------------------------------------------------

def test_validate_full_skip_shacl() -> None:
    builder = CelineGraphBuilder()
    nodes = _nodes("rec_community.yaml", "community_detail.json")
    doc, shacl_result = builder.validate_full(nodes, skip_shacl=True)
    assert "@graph" in doc
    assert shacl_result is None


def test_validate_full_with_shacl() -> None:
    builder = CelineGraphBuilder()
    nodes = _nodes("obs_meter_energy.yaml", "meter_data_rows.json")
    doc, shacl_result = builder.validate_full(nodes, skip_shacl=False)
    assert shacl_result is not None
    assert shacl_result.conforms is True
