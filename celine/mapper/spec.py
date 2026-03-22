"""MappingSpec: declarative field→ontology-term mapping definitions."""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

import jsonschema
import yaml

_SCHEMA_PATH = Path(__file__).parent / "schema" / "mapping_spec.schema.json"


@dataclass(frozen=True)
class FieldMapping:
    """Mapping rule for one field in an input row."""

    target: str
    source: str | None = None
    kind: Literal["literal", "iri", "nested", "constant"] = "literal"
    datatype: str | None = None
    required: bool = False
    iri_template: str | None = None
    value: Any = None
    nested_type: str | None = None
    nested_fields: tuple[FieldMapping, ...] = field(default_factory=tuple)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "FieldMapping":
        nested = tuple(
            FieldMapping.from_dict(f) for f in data.get("nested_fields", [])
        )
        return cls(
            source=data.get("source"),
            target=data["target"],
            kind=data.get("kind", "literal"),
            datatype=data.get("datatype"),
            required=data.get("required", False),
            iri_template=data.get("iri_template"),
            value=data.get("value"),
            nested_type=data.get("nested_type"),
            nested_fields=nested,
        )


@dataclass(frozen=True)
class MappingSpec:
    """Declarative spec mapping an input dict to a JSON-LD node."""

    version: str
    target_type: str
    id_template: str
    fields: tuple[FieldMapping, ...]
    context_vars: tuple[str, ...] = field(default_factory=tuple)
    label_template: str | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "MappingSpec":
        return cls(
            version=data["version"],
            target_type=data["target_type"],
            id_template=data["id_template"],
            fields=tuple(FieldMapping.from_dict(f) for f in data.get("fields", [])),
            context_vars=tuple(data.get("context_vars", [])),
            label_template=data.get("label_template"),
        )

    @classmethod
    def from_yaml(cls, path: Path) -> "MappingSpec":
        return MappingSpecLoader().load(path)

    @classmethod
    def from_yaml_string(cls, text: str) -> "MappingSpec":
        return MappingSpecLoader().load_from_string(text)


class SpecValidationError(ValueError):
    """Raised when a MappingSpec YAML fails schema validation."""


class MappingSpecLoader:
    """Loads and validates MappingSpec YAML files against mapping_spec.schema.json."""

    def __init__(self, schema_path: Path = _SCHEMA_PATH) -> None:
        with schema_path.open() as fh:
            self._schema: dict[str, Any] = json.load(fh)

    def load(self, path: Path) -> MappingSpec:
        with path.open() as fh:
            data = yaml.safe_load(fh)
        return self._parse(data, source=str(path))

    def load_from_string(self, text: str, source: str = "<string>") -> MappingSpec:
        data = yaml.safe_load(text)
        return self._parse(data, source=source)

    def _parse(self, data: Any, source: str) -> MappingSpec:
        try:
            jsonschema.validate(data, self._schema)
        except jsonschema.ValidationError as exc:
            raise SpecValidationError(
                f"Invalid MappingSpec in {source}: {exc.message} "
                f"(at {' > '.join(str(p) for p in exc.absolute_path)})"
            ) from exc
        return MappingSpec.from_dict(data)
