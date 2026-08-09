"""MappingSpec: declarative field→ontology-term mapping definitions."""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from importlib import resources
from pathlib import Path
from typing import Any, Literal

import jsonschema
import yaml

_SCHEMA_PATH = Path(__file__).parent / "schema" / "mapping_spec.schema.json"


def _specs_dir():
    """Traversable for the packaged ``specs/`` directory.

    Addressed as a subpath of ``celine.mapper`` rather than as the package
    ``celine.mapper.specs``: the directory has no ``__init__.py``, so naming it
    directly relies on namespace-package resolution that varies by loader. A
    joinpath from the parent works the same from a checkout, a wheel and a zip.
    """
    return resources.files(__package__).joinpath("specs")


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

    def load_by_name(self, name: str) -> MappingSpec:
        """Load one of the packaged specs by name, e.g. ``"obs_rec_energy"``.

        Resolved through ``importlib.resources``, not a filesystem path, so it
        works from an installed wheel as well as a checkout. Consumers bind a
        dataset to a spec by *name* (dataset-api stores it in
        ``DatasetEntry.ontology_path``), and a name is the only form that
        survives being written into a governance file and read back somewhere
        else entirely.

        Raises:
            SpecValidationError: no such spec. The message lists what is
                available, because the usual cause is a typo in a governance
                file written in another repository.
        """
        resource = _specs_dir().joinpath(f"{name}.yaml")
        if not resource.is_file():
            available = sorted(
                p.name.removesuffix(".yaml")
                for p in _specs_dir().iterdir()
                if p.name.endswith(".yaml")
            )
            raise SpecValidationError(
                f"no mapping spec named {name!r}. Available: {', '.join(available)}"
            )
        return self._parse(
            yaml.safe_load(resource.read_text(encoding="utf-8")),
            source=f"{name}.yaml",
        )

    @staticmethod
    def available() -> list[str]:
        """Names of every packaged spec, for validating a binding before storing it."""
        return sorted(
            p.name.removesuffix(".yaml")
            for p in _specs_dir().iterdir()
            if p.name.endswith(".yaml")
        )

    def _parse(self, data: Any, source: str) -> MappingSpec:
        try:
            jsonschema.validate(data, self._schema)
        except jsonschema.ValidationError as exc:
            raise SpecValidationError(
                f"Invalid MappingSpec in {source}: {exc.message} "
                f"(at {' > '.join(str(p) for p in exc.absolute_path)})"
            ) from exc
        return MappingSpec.from_dict(data)
