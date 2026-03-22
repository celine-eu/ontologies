"""CelineGraphBuilder: assembles JSON-LD documents and runs SHACL validation."""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import jsonschema
import rdflib

_RELEASES_DIR = Path(__file__).resolve().parent.parent.parent / "releases" / "v0.2"
_CONTEXT_PATH = _RELEASES_DIR / "celine.jsonld"
_SHACL_PATH = _RELEASES_DIR / "celine.shacl.ttl"
_SCHEMA_PATH = _RELEASES_DIR / "celine.schema.json"


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
        context_path: Path to celine.jsonld (default: bundled releases/v0.2/).
        shacl_path: Path to celine.shacl.ttl (default: bundled releases/v0.2/).
        schema_path: Path to celine.schema.json (default: bundled releases/v0.2/).
    """

    def __init__(
        self,
        context_path: Path = _CONTEXT_PATH,
        shacl_path: Path = _SHACL_PATH,
        schema_path: Path = _SCHEMA_PATH,
    ) -> None:
        self._shacl_path = shacl_path
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
                "Install it with: pip install pyshacl"
            ) from exc

        shacl_graph = rdflib.Graph()
        shacl_graph.parse(str(self._shacl_path), format="turtle")

        conforms, report_graph, report_text = pyshacl.validate(
            data_graph=graph,
            shacl_graph=shacl_graph,
            inference="none",
            abort_on_first=False,
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
