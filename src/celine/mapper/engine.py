"""MappingEngine: applies a MappingSpec to input dicts, producing JSON-LD node dicts."""
from __future__ import annotations

from functools import lru_cache
from typing import Any, Callable

from jinja2 import StrictUndefined, TemplateError, UndefinedError
from jinja2.sandbox import SandboxedEnvironment

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


# Two template dialects, selected by the spec's *format* version — never sniffed
# from the template's content. Sniffing would make the meaning of a `{` depend on
# whether a `{{` happened to appear elsewhere in the same file.
#
# `"1"` is `str.format_map` and single-brace `{var}`. It is what every spec written
# before 2026-09 uses, including specs living in other repositories (celine-pipelines,
# digital-twin) that this package cannot see and must not break.
#
# `"2"` is Jinja, which the schema had been *claiming* for these fields since they
# were written while the implementation was `format_map` throughout.

_JINJA_ENV = SandboxedEnvironment(
    # StrictUndefined, not the default Undefined, and this is the load-bearing choice.
    # Jinja's default renders a missing variable as the empty string, so `v1`'s
    # MappingError for a typo'd column would have become a *silently truncated IRI* —
    # the same class of failure as a shapes graph that fails to parse and reports
    # conforms=True. A template that names something the row does not carry must fail.
    undefined=StrictUndefined,
    # These render IRIs and labels, never HTML. Escaping would corrupt a query string.
    autoescape=False,
)


@lru_cache(maxsize=512)
def _compile(template_str: str):
    """Compile once per distinct template.

    `map_many` renders every template once per row; without this a 1000-row sample
    recompiles the same handful of templates 1000 times.
    """
    return _JINJA_ENV.from_string(template_str)


def _render_v1(template_str: str, variables: dict[str, Any]) -> str:
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


def _render_v2(template_str: str, variables: dict[str, Any]) -> str:
    """Render a ``{{ variable }}`` template through the Jinja sandbox.

    Values keep their native types so filters work on them (``| round``,
    ``| int``), unlike v1 which stringified everything up front.

    None is still rendered as the empty string, matching v1. That is parity and
    not an endorsement: a null joined into an `id_template` collapses distinct
    rows onto one IRI, which is exactly the defect recorded against
    `digital-twin`'s `obs_rec_energy`. Guarding it is a behaviour change to real
    emitted data and belongs to its own step, not to a syntax migration.
    """
    safe_vars = {k: ("" if v is None else v) for k, v in variables.items()}
    try:
        return _compile(template_str).render(**safe_vars)
    except UndefinedError as exc:
        raise MappingError(
            f"Template '{template_str}' references unknown variable: {exc}"
        ) from exc
    except TemplateError as exc:
        # Covers SecurityError from the sandbox and TemplateSyntaxError alike —
        # both are "this template cannot be rendered", which is what the caller
        # needs to know, and both carry their own message.
        raise MappingError(
            f"Template '{template_str}' could not be rendered: {exc}"
        ) from exc


_RENDERERS: dict[str, Callable[[str, dict[str, Any]], str]] = {
    "1": _render_v1,
    "2": _render_v2,
}


#: Base IRI for entities a mapping mints, when the caller sets none.
#:
#: Not a w3id.org URL, on purpose. `https://w3id.org/celine/…` is not a registered
#: namespace, so the previous default minted permanent-looking identifiers that
#: answer 404 everywhere — and because `base_uri` was only ever applied to a
#: *relative* `id_template` while every packaged spec was absolute, it was dead
#: code that no test touched. A default that is visibly unconfigured is better than
#: one that quietly claims a permanent identity. The real value is deployment
#: configuration, matching the house style of `dataset-api`'s `dataset_base_uri`.
DEFAULT_BASE_URI = "http://api.celine.localhost/entities"


def _is_templated(value: str, version: str) -> bool:
    """Whether a constant's string value should be run through the renderer."""
    if version == "2":
        return "{{" in value or "{%" in value
    return "{" in value


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
        spec: The MappingSpec describing the mapping rules. Its ``version`` selects
            the template dialect — ``"1"`` for ``{var}``, ``"2"`` for Jinja.
        context: Optional dict of variables available in id_template and iri_template
                 beyond the raw row fields. Typically EntityInfo.metadata.
        base_uri: Base IRI for the **entities this mapping mints** — applied to any
            ``id_template`` or ``iri_template`` output that is not already absolute.

    On ``base_uri``. It is deliberately *not* applied to ``kind: constant`` values:
    a constant here names an **ontology term** (a `sosa:observedProperty`, a scheme
    member), which belongs to whoever publishes the vocabulary and is not this
    service's to rename. Entities are minted by the service that serves them;
    terms are not. Conflating the two would rewrite every property IRI in the graph
    the first time a deployment set its own base.
    """

    def __init__(
        self,
        spec: MappingSpec,
        context: dict[str, Any] | None = None,
        base_uri: str = DEFAULT_BASE_URI,
    ) -> None:
        self._spec = spec
        self._context: dict[str, Any] = context or {}
        self._base_uri = base_uri.rstrip("/")
        try:
            self._render = _RENDERERS[spec.version]
        except KeyError:
            raise MappingError(
                f"Unknown mapping spec format version {spec.version!r}. "
                f"Known: {', '.join(sorted(_RENDERERS))}."
            ) from None

    def _absolutize(self, iri: str) -> str:
        """Apply the configured base to a relative IRI; leave an absolute one alone.

        Used for both ``id_template`` and ``iri_template``. ``iri_template`` never
        had a base applied at all before this, so a spec whose ``id_template`` was
        made relative while its ``iri_template`` was not would have emitted subjects
        under the configured base and object references under a dead namespace —
        a graph whose two halves disagree about where its entities live.
        """
        if not iri or iri.startswith("http://") or iri.startswith("https://"):
            return iri
        return f"{self._base_uri}/{iri.lstrip('/')}"

    def map_one(self, row: dict[str, Any]) -> dict[str, Any]:
        """Map a single input dict to a JSON-LD node dict.

        Returns a dict with ``@id``, ``@type``, and all mapped properties.
        Nested sub-nodes are embedded inline under their property key.

        Raises:
            MappingError: if a required field is missing.
        """
        variables = {**self._context, **row}

        node_id = self._absolutize(self._render(self._spec.id_template, variables))

        node: dict[str, Any] = {
            "@id": node_id,
            "@type": self._spec.target_type,
        }

        if self._spec.label_template:
            label = self._render(self._spec.label_template, variables)
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
        # If the constant value is a template, render it from context vars. What
        # counts as a template depends on the dialect: under v1 a bare `{` is one,
        # under v2 only `{{`/`{%` are — so a v2 constant may contain a literal brace.
        if isinstance(val, str) and _is_templated(val, self._spec.version):
            val = self._render(val, variables)
        # No base is applied: a constant names an ontology term, not an entity.
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
            iri = self._render(
                fm.iri_template,
                {**variables, "value": str(value) if value is not None else ""},
            )
        else:
            iri = str(value) if value is not None else ""

        if not iri:
            return None
        # The base applies here too. Without it a bare column value became the
        # `@id` verbatim — not a valid IRI, so rdflib dropped the node and the
        # graph came out smaller than the sample, which SHACL reports as
        # conforming. See the plan's "an empty graph conforms" note.
        return (fm.target, {"@id": self._absolutize(iri)})

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
