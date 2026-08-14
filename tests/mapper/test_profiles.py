"""Tests for ontology profile resolution.

The bug these exist to prevent is not subtle and has already happened once: the
graph builder resolved its artifacts by walking ``__file__`` up to
``specs/current``, which in an installed environment is a directory that cannot
exist, and every deployed consumer failed at construction. Nothing caught it
because the only callers were this repo's own tests, running from the checkout
where the walk happens to work.

So these tests deliberately avoid asserting anything about *paths*. They assert
that a profile resolves, that its shapes graph is non-empty, and that the version
that ran is the version that was asked for.
"""
from __future__ import annotations

import json

import pytest

from celine.mapper.graph import GraphBuilder
from celine.mapper.profiles import (
    Profile,
    ProfileError,
    ProfileNotFoundError,
    available_profiles,
    load_profile,
    load_profile_from_dir,
)
from celine.mapper.spec import MappingSpecLoader

#: The packaging policy, restated as a test. `pyproject.toml` force-includes
#: exactly these versions; a dataset may pin any of them and must still resolve.
#: Dropping one from the wheel without deciding to drop it fails here.
SHIPPED_VERSIONS = ("v0.8", "v0.9", "v0.10")

_loader = MappingSpecLoader()


# ---------------------------------------------------------------------------
# Discovery
# ---------------------------------------------------------------------------

def test_celine_profile_is_available() -> None:
    found = available_profiles()
    assert "celine" in found
    assert set(SHIPPED_VERSIONS) <= set(found["celine"])


def test_versions_sort_numerically_not_lexically() -> None:
    """v0.10 is newer than v0.9. A string sort disagrees."""
    versions = available_profiles()["celine"]
    assert versions.index("v0.10") > versions.index("v0.9")
    assert load_profile("celine").version == versions[-1]


def test_current_is_not_listed_as_a_version() -> None:
    """`specs/current/` is a copy of the newest version, not a version.

    Listing it would give "what can I pin to" two answers for the same bytes.
    """
    assert "current" not in available_profiles()["celine"]


# ---------------------------------------------------------------------------
# Loading
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("version", SHIPPED_VERSIONS)
def test_every_shipped_version_loads_completely(version: str) -> None:
    profile = load_profile("celine", version)
    assert isinstance(profile, Profile)
    assert profile.version == version
    assert profile.context, "empty @context"
    assert profile.json_schema, "empty JSON Schema"
    assert profile.shapes_ttl.strip(), "empty shapes"
    assert profile.ontology_ttl.strip(), "empty ontology"


@pytest.mark.parametrize("version", SHIPPED_VERSIONS)
def test_shapes_parse_to_a_non_empty_graph(version: str) -> None:
    """A shapes graph that failed to parse reports `conforms=True` on anything.

    That is indistinguishable from a check that never ran, which is why the
    builder refuses it and why every shipped version is checked rather than
    just the newest.
    """
    rdflib = pytest.importorskip("rdflib")
    graph = rdflib.Graph()
    graph.parse(data=load_profile("celine", version).shapes_ttl, format="turtle")
    assert len(graph) > 0


def test_unknown_profile_names_what_is_available() -> None:
    with pytest.raises(ProfileNotFoundError) as exc:
        load_profile("brick")
    assert "celine" in str(exc.value)


def test_aged_out_pin_names_the_pin_and_the_window() -> None:
    """A pin older than the shipped window must fail loudly, not silently
    fall back to the newest — falling back would validate against shapes the
    dataset never claimed."""
    with pytest.raises(ProfileNotFoundError) as exc:
        load_profile("celine", "v0.99")
    message = str(exc.value)
    assert "v0.99" in message
    assert "v0.10" in message


def test_load_from_dir_accepts_the_specs_naming(tmp_path) -> None:
    source = load_profile("celine", "v0.10")
    (tmp_path / "celine.ttl").write_text(source.ontology_ttl, encoding="utf-8")
    (tmp_path / "celine.shacl.ttl").write_text(source.shapes_ttl, encoding="utf-8")
    (tmp_path / "celine.jsonld").write_text(
        json.dumps({"@context": source.context}), encoding="utf-8"
    )
    (tmp_path / "celine.schema.json").write_text(
        json.dumps(source.json_schema), encoding="utf-8"
    )
    profile = load_profile_from_dir(tmp_path, name="vendored", version="local")
    assert profile.source == "explicit"
    assert profile.context == source.context


def test_incomplete_profile_is_refused(tmp_path) -> None:
    """Three of four artifacts is not a usable profile: validating against a
    partial one reports conformance it never checked."""
    (tmp_path / "ontology.ttl").write_text("", encoding="utf-8")
    with pytest.raises(ProfileError) as exc:
        load_profile_from_dir(tmp_path)
    assert "shapes.ttl" in str(exc.value)


# ---------------------------------------------------------------------------
# Pinning — the point of the whole exercise
# ---------------------------------------------------------------------------

def test_packaged_specs_are_pinned() -> None:
    """Every shipped mapping spec declares its profile.

    Unpinned is legal, but it should mean something specific rather than being
    the common case.
    """
    for name in MappingSpecLoader.available():
        spec = _loader.load_by_name(name)
        assert spec.profile is not None, f"{name} declares no profile"
        assert spec.profile.version, f"{name} declares a profile with no version pin"


def test_builder_honours_the_specs_pin() -> None:
    spec = _loader.load_by_name("obs_rec_energy")
    builder = GraphBuilder.for_spec(spec)
    assert builder.profile.version == spec.profile.version


def test_override_answers_the_upgrade_question() -> None:
    """`--profile-version` exists so an upgrade is decided, not discovered."""
    spec = _loader.load_by_name("obs_rec_energy")
    builder = GraphBuilder.for_spec(spec, version="v0.8")
    assert builder.profile.version == "v0.8"
    assert spec.profile.version != "v0.8", "fixture no longer proves an override happened"


def test_result_reports_which_shapes_ran() -> None:
    """`conforms` alone is not a claim — against which version is half of it."""
    pytest.importorskip("pyshacl")
    spec = _loader.load_by_name("obs_rec_energy")
    builder = GraphBuilder.for_spec(spec)
    document = builder.build_document([])
    result = builder.validate_shacl(builder.to_rdf_graph(document))
    assert result.profile_name == "celine"
    assert result.profile_version == builder.profile.version
    assert builder.profile.version in str(result)
