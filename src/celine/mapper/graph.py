"""GraphBuilder: assembles JSON-LD documents and runs SHACL validation.

The artifacts come from an ontology :class:`~celine.mapper.profiles.Profile` —
a named vocabulary at a pinned version — rather than from paths resolved
relative to this source tree. The previous defaults walked ``__file__`` up to
``specs/current``, which in an installed environment is
``<site-packages>/specs/current`` and does not exist; every deployed consumer
failed at construction. See ``profiles.py``.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any

import jsonschema

from celine.mapper.profiles import (
    DEFAULT_PROFILE,
    Profile,
    load_profile,
    load_profile_from_dir,
)

if TYPE_CHECKING:
    import rdflib

    from celine.mapper.spec import MappingSpec


@dataclass
class SHACLResult:
    """Result of a pyshacl validation run."""

    conforms: bool
    violations: list[str] = field(default_factory=list)
    report_graph: rdflib.Graph | None = None
    # Which shapes actually ran. A conformance claim is meaningless without the
    # version it was made against — "conforms" against v0.8 and against v0.10
    # are different statements, and a caller that only sees a boolean cannot
    # tell them apart.
    profile_name: str | None = None
    profile_version: str | None = None

    def __str__(self) -> str:
        against = ""
        if self.profile_name:
            against = f" (against {self.profile_name} {self.profile_version})"
        if self.conforms:
            return f"SHACL: conforms{against}"
        lines = [f"SHACL: does NOT conform{against}"] + [f"  - {v}" for v in self.violations]
        return "\n".join(lines)


class GraphBuilder:
    """Assembles mapped nodes into a JSON-LD document and validates it.

    Args:
        profile: the ontology profile to validate against. A :class:`Profile`,
            a ``"name"`` string, or ``None`` for the newest CELINE profile
            available. Pass a resolved profile when the caller needs to report
            *which* version ran — which any conformance report does.
        version: version pin, used only when ``profile`` is a name or ``None``.
        artifacts_dir: a directory holding the four artifacts, for a profile that
            is neither packaged nor in a known checkout.

    The pin matters. A dataset's mapping asserts conformance against the
    ontology version it was written for, and a newer release must not decide
    retroactively that it stopped conforming. ``profile.version`` on the
    resolved profile is the value to report — never the argument passed in,
    which may have been ``None``.
    """

    def __init__(
        self,
        profile: Profile | str | None = None,
        version: str | None = None,
        artifacts_dir: Path | None = None,
    ) -> None:
        if artifacts_dir is not None:
            resolved = load_profile_from_dir(artifacts_dir)
        elif isinstance(profile, Profile):
            resolved = profile
        else:
            resolved = load_profile(profile or DEFAULT_PROFILE, version)

        self.profile: Profile = resolved
        self._context: dict[str, Any] = resolved.context
        self._json_schema: dict[str, Any] = resolved.json_schema

    @classmethod
    def for_spec(
        cls,
        spec: "MappingSpec",
        profile: str | None = None,
        version: str | None = None,
    ) -> "GraphBuilder":
        """Build the validator a mapping spec declares.

        Precedence: an explicit argument, then the spec's own ``profile`` pin,
        then the newest CELINE profile. The override exists for one deliberate
        question — *would this mapping still conform under version N+1?* — which
        is how an upgrade gets decided rather than discovered.
        """
        pin = getattr(spec, "profile", None)
        return cls(
            profile=profile or (pin.name if pin else DEFAULT_PROFILE),
            version=version or (pin.version if pin else None),
        )

    # ------------------------------------------------------------------
    # Document assembly
    # ------------------------------------------------------------------

    def build_document(self, nodes: list[dict[str, Any]]) -> dict[str, Any]:
        """Wrap nodes in a JSON-LD document with the CELINE context.

        Returns:
            ``{"@context": ..., "@graph": nodes}``
        """
        return {"@context": self._context, "@graph": nodes}

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------

    def validate_json_schema(self, document: dict[str, Any]) -> None:
        """Validate document against celine.schema.json.

        Raises:
            jsonschema.ValidationError: on structural violations.
        """
        jsonschema.validate(document, self._json_schema)

    def to_rdf_graph(self, document: dict[str, Any]) -> rdflib.Graph:
        """Parse a JSON-LD document into an rdflib Graph."""
        try:
            import rdflib  # noqa: PLC0415
        except ImportError as exc:
            raise ImportError(
                "rdflib is required for RDF graph operations. "
                "Install it with: pip install celine-ontologies[mapper]"
            ) from exc
        g = rdflib.Graph()
        g.parse(data=json.dumps(document), format="json-ld")
        return g

    def validate_shacl(self, graph: rdflib.Graph) -> SHACLResult:
        """Run pyshacl against celine.shacl.ttl.

        Args:
            graph: An rdflib Graph containing the data to validate.

        Returns:
            SHACLResult with ``conforms`` flag and list of violation messages.
        """
        try:
            import pyshacl  # noqa: PLC0415
        except ImportError as exc:
            raise ImportError(
                "pyshacl is required for SHACL validation. "
                "Install it with: pip install celine-ontologies[mapper]"
            ) from exc

        try:
            import rdflib  # noqa: PLC0415
        except ImportError as exc:
            raise ImportError(
                "rdflib is required for SHACL validation. "
                "Install it with: pip install celine-ontologies[mapper]"
            ) from exc

        # Parsed from text, not from a path: a packaged profile may live inside
        # a zip, where no filesystem path exists.
        shacl_graph = rdflib.Graph()
        shacl_graph.parse(data=self.profile.shapes_ttl, format="turtle")
        if len(shacl_graph) == 0:
            # An empty shapes graph reports `conforms=True` against anything.
            # That is the exact signature of a check that never ran, so it is
            # refused rather than reported as a pass.
            raise ValueError(
                f"profile {self.profile} parsed to an empty shapes graph — "
                f"nothing would be validated"
            )

        # The ontology must be validated alongside the data, not just the shapes.
        # Several scheme constraints are written with `sh:targetNode` (e.g.
        # celine:MemberRoleSchemeShape targets celine:MemberRole and requires
        # skos:hasTopConcept minCount 1). A targetNode shape fires against *any*
        # data graph, whether or not that node appears in it — so without the
        # vocabulary definitions present, validating a graph of pure instance
        # data reports a dozen violations about concept schemes the data never
        # mentions, and no instance document can ever conform.
        #
        # pyshacl's `ont_graph=` parameter does *not* solve this: by default it
        # merges via `inoculate()`, which copies only RDFS/OWL class and property
        # axioms. SKOS ConceptScheme nodes and their skos:hasTopConcept triples
        # are dropped, so the scheme shapes keep firing. (The full mixin lives
        # behind the PYSHACL_USE_FULL_MIXIN env var, read at import time — not
        # something a library should reach for.) Merging into a copy of the data
        # graph ourselves is explicit and version-independent; the caller's graph
        # is left untouched.
        combined = rdflib.Graph()
        for prefix, namespace in graph.namespaces():
            combined.bind(prefix, namespace)
        combined += graph
        combined.parse(data=self.profile.ontology_ttl, format="turtle")

        # `advanced=True` is required, not optional. A large share of the profile
        # — every `*ConceptShape`, and the v0.10 `celine:DefinedTermLabelShape`
        # that guards against one IRI being minted twice — selects its focus
        # nodes with `sh:target [ a sh:SPARQLTarget ]`. That is a SHACL Advanced
        # Features construct; with advanced off pyshacl does not report it as
        # unsupported, it simply finds no focus nodes and those shapes pass
        # vacuously. The profile then validates everything it was written to
        # catch.
        conforms, report_graph, report_text = pyshacl.validate(
            data_graph=combined,
            shacl_graph=shacl_graph,
            inference="none",
            abort_on_first=False,
            advanced=True,
        )

        violations: list[str] = []
        if not conforms:
            # Extract violation messages from report text
            for line in report_text.splitlines():
                line = line.strip()
                if line and not line.startswith("Validation Report"):
                    violations.append(line)

        return SHACLResult(
            conforms=conforms,
            violations=violations,
            report_graph=report_graph,
            profile_name=self.profile.name,
            profile_version=self.profile.version,
        )

    # ------------------------------------------------------------------
    # Convenience pipeline
    # ------------------------------------------------------------------

    def validate_full(
        self,
        nodes: list[dict[str, Any]],
        skip_shacl: bool = False,
    ) -> tuple[dict[str, Any], SHACLResult | None]:
        """Build document, run JSON Schema validation, optionally run SHACL.

        Returns:
            Tuple of (document, shacl_result). shacl_result is None if skipped.

        Raises:
            jsonschema.ValidationError: on JSON Schema violations.
        """
        doc = self.build_document(nodes)
        self.validate_json_schema(doc)
        shacl_result = None
        if not skip_shacl:
            rdf_graph = self.to_rdf_graph(doc)
            shacl_result = self.validate_shacl(rdf_graph)
        return doc, shacl_result


class CelineGraphBuilder(GraphBuilder):
    """``GraphBuilder`` pinned to the CELINE profile.

    A back-compat alias, kept because consumers (dataset-api, digital-twin, this
    repo's own tests and CLI) import this name. New code should use
    ``GraphBuilder`` and name its profile: the vocabulary layer is plural — a
    single mapping spec already spans SOSA, SEAS, SAREF and CIM — and CELINE is
    one profile among them rather than the shape of the concept.
    """

    def __init__(
        self,
        profile: Profile | str | None = None,
        version: str | None = None,
        artifacts_dir: Path | None = None,
    ) -> None:
        super().__init__(
            profile=profile or DEFAULT_PROFILE,
            version=version,
            artifacts_dir=artifacts_dir,
        )
