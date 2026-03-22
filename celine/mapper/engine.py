"""MappingEngine: applies a MappingSpec to input dicts, producing JSON-LD node dicts."""
from __future__ import annotations

from typing import Any

from celine.mapper.spec import FieldMapping, MappingSpec


class MappingError(ValueError):
    """Raised when a required field is missing or a template cannot be rendered."""

    def __init__(
        self,
        message: str,
        field_name: str | None = None,
        row_index: int | None = None,
    ) -> None:
        super().__init__(message)
        self.field_name = field_name
        self.row_index = row_index


def _render(template_str: str, variables: dict[str, Any]) -> str:
    """Render a ``{variable}`` template using str.format_map.

    None values are converted to empty strings. Missing variables raise
    MappingError.
    """
    safe_vars = {k: ("" if v is None else str(v)) for k, v in variables.items()}
    try:
        return template_str.format_map(safe_vars)
    except KeyError as exc:
        raise MappingError(
            f"Template '{template_str}' references unknown variable {exc}"
        ) from exc


def _coerce_value(value: Any, datatype: str | None) -> Any:
    """Return value in a JSON-LD-friendly form for the given XSD datatype."""
    if value is None:
        return None
    if datatype in ("xsd:decimal", "xsd:double", "xsd:float"):
        try:
            return float(value)
        except (TypeError, ValueError):
            return value
    if datatype in ("xsd:integer", "xsd:int", "xsd:long"):
        try:
            return int(value)
        except (TypeError, ValueError):
            return value
    if datatype == "xsd:boolean":
        if isinstance(value, bool):
            return value
        return str(value).lower() in ("true", "1", "yes")
    # For xsd:string, xsd:dateTime, etc. — stringify
    return str(value) if not isinstance(value, str) else value


def _nested_id(parent_id: str, target: str, index: int) -> str:
    """Generate a deterministic IRI for a nested sub-node."""
    slug = target.split(":")[-1].replace("_", "-")
    return f"{parent_id}/{slug}/{index}"


class MappingEngine:
    """Stateless transformer: (MappingSpec + context) → row dict → JSON-LD node dict.

    Args:
        spec: The MappingSpec describing the mapping rules.
        context: Optional dict of variables available in id_template and iri_template
                 beyond the raw row fields. Typically EntityInfo.metadata.
        base_uri: Fallback base IRI if id_template produces a relative path.
    """

    def __init__(
        self,
        spec: MappingSpec,
        context: dict[str, Any] | None = None,
        base_uri: str = "https://w3id.org/celine/",
    ) -> None:
        self._spec = spec
        self._context: dict[str, Any] = context or {}
        self._base_uri = base_uri.rstrip("/")

    def map_one(self, row: dict[str, Any]) -> dict[str, Any]:
        """Map a single input dict to a JSON-LD node dict.

        Returns a dict with ``@id``, ``@type``, and all mapped properties.
        Nested sub-nodes are embedded inline under their property key.

        Raises:
            MappingError: if a required field is missing.
        """
        variables = {**self._context, **row}

        node_id = _render(self._spec.id_template, variables)
        if not node_id.startswith("http"):
            node_id = f"{self._base_uri}/{node_id.lstrip('/')}"

        node: dict[str, Any] = {
            "@id": node_id,
            "@type": self._spec.target_type,
        }

        if self._spec.label_template:
            label = _render(self._spec.label_template, variables)
            if label:  # skip empty/None-derived labels
                node["rdfs:label"] = label

        for fm in self._spec.fields:
            result = self._apply_field(fm, row, variables, node_id)
            if result is None:
                continue
            prop, value = result
            # Merge list values
            if prop in node:
                existing = node[prop]
                if isinstance(existing, list):
                    if isinstance(value, list):
                        existing.extend(value)
                    else:
                        existing.append(value)
                else:
                    node[prop] = [existing, value] if not isinstance(value, list) else [existing] + value
            else:
                node[prop] = value

        return node

    def map_many(self, rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Map a list of input dicts.  All rows are mapped; errors propagate."""
        return [self.map_one(row) for row in rows]

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _apply_field(
        self,
        fm: FieldMapping,
        row: dict[str, Any],
        variables: dict[str, Any],
        parent_id: str,
    ) -> tuple[str, Any] | None:
        """Return (property, value) or None if the field should be skipped."""

        if fm.kind == "constant":
            return (fm.target, self._apply_constant(fm, variables))

        if fm.kind == "literal":
            return self._apply_literal(fm, row, variables)

        if fm.kind == "iri":
            return self._apply_iri(fm, row, variables)

        if fm.kind == "nested":
            return self._apply_nested(fm, row, variables, parent_id)

        return None

    def _get_source_value(
        self, fm: FieldMapping, row: dict[str, Any]
    ) -> Any:
        """Extract source field value, respecting required flag."""
        value = row.get(fm.source) if fm.source else None
        if fm.required and (value is None or (isinstance(value, str) and not value.strip())):
            raise MappingError(
                f"Required field '{fm.source}' is missing or empty.",
                field_name=fm.source,
            )
        return value

    def _apply_constant(
        self, fm: FieldMapping, variables: dict[str, Any]
    ) -> Any:
        val = fm.value
        # If the constant value is a {template}, render it from context vars
        if isinstance(val, str) and "{" in val:
            val = _render(val, variables)
        return val

    def _apply_literal(
        self,
        fm: FieldMapping,
        row: dict[str, Any],
        variables: dict[str, Any],
    ) -> tuple[str, Any] | None:
        value = self._get_source_value(fm, row)
        if value is None:
            return None
        coerced = _coerce_value(value, fm.datatype)
        return (fm.target, coerced)

    def _apply_iri(
        self,
        fm: FieldMapping,
        row: dict[str, Any],
        variables: dict[str, Any],
    ) -> tuple[str, Any] | None:
        if fm.source:
            value = self._get_source_value(fm, row)
            if value is None:
                return None
        else:
            # No source — IRI is derived purely from context vars via iri_template
            value = None

        if fm.iri_template:
            iri = _render(fm.iri_template, {**variables, "value": str(value) if value is not None else ""})
        else:
            iri = str(value) if value is not None else ""

        if not iri:
            return None
        return (fm.target, {"@id": iri})

    def _apply_nested(
        self,
        fm: FieldMapping,
        row: dict[str, Any],
        variables: dict[str, Any],
        parent_id: str,
    ) -> tuple[str, list[dict[str, Any]]] | None:
        value = self._get_source_value(fm, row)
        if value is None:
            return None

        items = value if isinstance(value, list) else [value]
        sub_nodes: list[dict[str, Any]] = []

        for idx, item in enumerate(items):
            if not isinstance(item, dict):
                continue
            sub_id = _nested_id(parent_id, fm.target, idx)
            sub_node: dict[str, Any] = {
                "@id": sub_id,
                "@type": fm.nested_type,
            }
            sub_vars = {**variables, **item}
            for sub_fm in fm.nested_fields:
                result = self._apply_field(sub_fm, item, sub_vars, sub_id)
                if result is None:
                    continue
                prop, val = result
                sub_node[prop] = val
            sub_nodes.append(sub_node)

        if not sub_nodes:
            return None
        return (fm.target, sub_nodes if len(sub_nodes) > 1 else sub_nodes[0])
