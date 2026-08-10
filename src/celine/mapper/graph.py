"""CelineGraphBuilder: assembles JSON-LD documents and runs SHACL validation."""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any

import jsonschema

if TYPE_CHECKING:
    import rdflib

# `specs/current`, not `releases/`: the two trees hold different artifacts.
# `releases/vN` carries the Widoco build (`ontology.jsonld|ttl|owl|nt`); the
# `celine.*` files these defaults want are only ever in `specs/`. The previous
# value — `parent.parent.parent / "releases" / "v0.2"` — was wrong three ways at
# once: it walked to `src/` rather than the repo root, named a directory holding
# none of these files, and pinned v0.2 while specs had reached v0.7. Nothing
# noticed because every failure is a FileNotFoundError at construction, and the
# only callers that exercise it are this repo's own tests and CLI.
_SPECS_DIR = Path(__file__).resolve().parents[3] / "specs" / "current"
_CONTEXT_PATH = _SPECS_DIR / "celine.jsonld"
_SHACL_PATH = _SPECS_DIR / "celine.shacl.ttl"
_SCHEMA_PATH = _SPECS_DIR / "celine.schema.json"
_ONTOLOGY_PATH = _SPECS_DIR / "celine.ttl"


def _load_context() -> dict[str, Any]:
    """Load the @context block from celine.jsonld."""
    with _CONTEXT_PATH.open() as fh:
        doc = json.load(fh)
    return doc["@context"]


def _load_json_schema() -> dict[str, Any]:
    with _SCHEMA_PATH.open() as fh:
        return json.load(fh)


@dataclass
class SHACLResult:
    """Result of a pyshacl validation run."""

    conforms: bool
    violations: list[str] = field(default_factory=list)
    report_graph: rdflib.Graph | None = None

    def __str__(self) -> str:
        if self.conforms:
            return "SHACL: conforms"
        lines = ["SHACL: does NOT conform"] + [f"  - {v}" for v in self.violations]
        return "\n".join(lines)


class CelineGraphBuilder:
    """Assembles mapped nodes into a JSON-LD document and validates it.

    Args:
        context_path: Path to celine.jsonld (default: ``specs/current/``).
        shacl_path: Path to celine.shacl.ttl (default: ``specs/current/``).
        schema_path: Path to celine.schema.json (default: ``specs/current/``).

    The defaults resolve relative to this repository and therefore only work from
    a source checkout — ``specs/`` is outside the wheel's ``only-include``. An
    installed consumer must pass all three explicitly.
    """

    def __init__(
        self,
        context_path: Path = _CONTEXT_PATH,
        shacl_path: Path = _SHACL_PATH,
        schema_path: Path = _SCHEMA_PATH,
        ontology_path: Path = _ONTOLOGY_PATH,
    ) -> None:
        self._shacl_path = shacl_path
        self._ontology_path = ontology_path
        with context_path.open() as fh:
            raw = json.load(fh)
        self._context: dict[str, Any] = raw["@context"]
        with schema_path.open() as fh:
            self._json_schema: dict[str, Any] = json.load(fh)

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

        shacl_graph = rdflib.Graph()
        shacl_graph.parse(str(self._shacl_path), format="turtle")

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
        combined.parse(str(self._ontology_path), format="turtle")

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
