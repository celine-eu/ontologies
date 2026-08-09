"""The vocabulary registry as a prefix authority.

`open-repository.yaml` stopped being documentation the moment a consumer began
expanding CURIEs through it: dataset-api derives its per-dataset JSON-LD contexts
from this map, so a prefix missing here is a bare CURIE in a served document.
These tests pin the properties that consumer depends on.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import jsonschema
import pytest
import yaml

from celine.mapper import MappingSpecLoader, PrefixError, expand, load_registry, prefix_map

ROOT = Path(__file__).resolve().parents[2]
SPECS_DIR = ROOT / "src" / "celine" / "mapper" / "specs"
CONTEXT = ROOT / "specs" / "current" / "celine.jsonld"

_CURIE = re.compile(r"^([A-Za-z][\w.-]*):(?!//)")


def _prefixes_used_by(spec_file: Path) -> set[str]:
    """Every CURIE prefix appearing in a spec's target types and datatypes."""
    data = yaml.safe_load(spec_file.read_text(encoding="utf-8"))
    values = [data.get("target_type", "")]

    def walk(fields):
        for f in fields or []:
            values.append(f.get("target", ""))
            values.append(f.get("datatype") or "")
            walk(f.get("nested_fields"))

    walk(data.get("fields"))
    return {m.group(1) for v in values if (m := _CURIE.match(str(v)))}


def test_registry_validates_against_its_own_schema():
    """It did not, until 2026-08-08 — `src` was required, no entry had it, and it
    was not even a declared property. A schema nothing is checked against drifts
    into fiction, which is how the requirement survived unnoticed."""
    registry = yaml.safe_load((ROOT / "open-repository.yaml").read_text(encoding="utf-8"))
    schema = json.loads((ROOT / "open-repository.schema.json").read_text(encoding="utf-8"))
    jsonschema.validate(registry, schema)


@pytest.mark.parametrize(
    "spec_file", sorted(SPECS_DIR.glob("*.yaml")), ids=lambda p: p.stem
)
def test_every_prefix_a_spec_uses_is_resolvable(spec_file: Path):
    """The property that matters. A spec naming `sosa:` while the registry does
    not declare it yields a context a consumer cannot expand — and the failure
    surfaces in the consumer, not here, which is the whole reason this is a test
    in this repo."""
    unresolvable = _prefixes_used_by(spec_file) - set(prefix_map())
    assert not unresolvable, (
        f"{spec_file.name} uses {sorted(unresolvable)}, absent from "
        f"open-repository.yaml. Add them to the ontology's entry, or to the "
        f"top-level `prefixes:` map for a base vocabulary."
    )


def test_registry_agrees_with_the_ontologys_own_context():
    """Two holders of one fact: the registry and `celine.jsonld`'s @context both
    map prefixes to namespaces. They are allowed to cover different sets — the
    registry knows ontologies the profile never references — but where they
    overlap they must not disagree, or a term means one thing in a served context
    and another in the published ontology."""
    context = json.loads(CONTEXT.read_text(encoding="utf-8"))["@context"]
    disagreements = {
        prefix: (namespace, context[prefix])
        for prefix, namespace in prefix_map().items()
        if prefix in context and context[prefix] != namespace
    }
    assert not disagreements, f"registry vs celine.jsonld: {disagreements}"


def test_a_prefix_and_its_namespace_travel_together():
    """`dependentRequired` in the schema, asserted here against the real file:
    a prefix without a namespace expands to nothing, and a namespace without a
    prefix is unreachable."""
    for entry in load_registry().get("ontologies") or []:
        assert bool(entry.get("prefix")) == bool(entry.get("namespace")), (
            f"{entry['name']} declares only one of prefix/namespace"
        )


def test_expand_passes_absolute_iris_through():
    """Specs mix both forms — `sosa:resultTime` beside a full
    `https://w3id.org/celine/property/...` — so expansion has to be a no-op on
    the second."""
    iri = "https://w3id.org/celine/property/self-consumption-kw"
    assert expand(iri) == iri


def test_expand_raises_on_an_unknown_prefix():
    """Rather than returning the CURIE untouched. An unexpanded CURIE in a served
    JSON-LD context is not a smaller failure than a missing one — it is the same
    failure, discovered by the consumer instead of here."""
    with pytest.raises(PrefixError):
        expand("nosuchprefix:Term")


# ── load_by_name ──────────────────────────────────────────────────


def test_specs_are_loadable_by_name():
    """Consumers bind a dataset to a spec by name — dataset-api stores it in
    `DatasetEntry.ontology_path` — because a name is the only form that survives
    being written into a governance file in one repository and read in another."""
    spec = MappingSpecLoader().load_by_name("obs_rec_energy")
    assert spec.target_type == "sosa:Observation"


def test_available_lists_every_packaged_spec():
    assert set(MappingSpecLoader.available()) == {p.stem for p in SPECS_DIR.glob("*.yaml")}


def test_unknown_spec_name_lists_the_alternatives():
    """The usual cause is a typo in a governance file written elsewhere, so the
    error has to be readable by someone who cannot see this directory."""
    from celine.mapper import SpecValidationError

    with pytest.raises(SpecValidationError, match="obs_rec_energy"):
        MappingSpecLoader().load_by_name("obs_rec_enrgy")
