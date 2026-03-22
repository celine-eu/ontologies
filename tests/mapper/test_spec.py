"""Tests for MappingSpec loading and validation."""
from __future__ import annotations

from pathlib import Path

import pytest

from celine.mapper.spec import (
    FieldMapping,
    MappingSpec,
    MappingSpecLoader,
    SpecValidationError,
)

SPECS_DIR = Path(__file__).resolve().parent.parent.parent / "celine" / "mapper" / "specs"


def _loader() -> MappingSpecLoader:
    return MappingSpecLoader()


# ---------------------------------------------------------------------------
# Bundled spec loading
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("spec_file", [
    "rec_community.yaml",
    "rec_member.yaml",
    "rec_asset.yaml",
    "rec_delivery_point.yaml",
    "obs_rec_energy.yaml",
    "obs_meter_energy.yaml",
    "obs_pv_forecast.yaml",
    "obs_rec_forecast.yaml",
    "obs_meter_forecast.yaml",
])
def test_bundled_specs_load(spec_file: str) -> None:
    """All bundled spec files must load without errors."""
    spec = _loader().load(SPECS_DIR / spec_file)
    assert spec.version == "1"
    assert spec.target_type
    assert spec.id_template


def test_spec_is_frozen() -> None:
    spec = _loader().load(SPECS_DIR / "rec_community.yaml")
    with pytest.raises((AttributeError, TypeError)):
        spec.version = "2"  # type: ignore[misc]  # frozen dataclass must raise


# ---------------------------------------------------------------------------
# Inline YAML parsing
# ---------------------------------------------------------------------------

MINIMAL_YAML = """\
version: "1"
target_type: "peco:Renewable_energy_community"
id_template: "https://example.org/rec/{key}"
fields:
  - source: key
    target: "dct:identifier"
    required: true
"""


def test_load_from_string() -> None:
    spec = MappingSpecLoader().load_from_string(MINIMAL_YAML)
    assert spec.target_type == "peco:Renewable_energy_community"
    assert len(spec.fields) == 1
    assert spec.fields[0].source == "key"
    assert spec.fields[0].required is True


# ---------------------------------------------------------------------------
# Invalid spec → SpecValidationError
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("bad_yaml,match", [
    # Missing required top-level keys
    ('version: "1"\ntarget_type: "foo"\nfields: []', "id_template"),
    ('version: "1"\nid_template: "x"\nfields: []', "target_type"),
    # Wrong version
    ('version: "99"\ntarget_type: "foo"\nid_template: "x"\nfields: []', "version"),
    # Field with nested kind but no nested_type
    (
        'version: "1"\ntarget_type: "t"\nid_template: "x"\nfields:\n'
        '  - source: foo\n    target: "bar"\n    kind: nested\n',
        None,  # any SpecValidationError
    ),
    # Constant without value
    (
        'version: "1"\ntarget_type: "t"\nid_template: "x"\nfields:\n'
        '  - target: "bar"\n    kind: constant\n',
        None,
    ),
])
def test_invalid_spec_raises(bad_yaml: str, match: str | None) -> None:
    with pytest.raises(SpecValidationError):
        MappingSpecLoader().load_from_string(bad_yaml)


# ---------------------------------------------------------------------------
# FieldMapping.from_dict
# ---------------------------------------------------------------------------

def test_field_mapping_defaults() -> None:
    fm = FieldMapping.from_dict({"target": "dct:identifier"})
    assert fm.kind == "literal"
    assert fm.required is False
    assert fm.source is None


def test_field_mapping_nested_fields() -> None:
    fm = FieldMapping.from_dict({
        "source": "delivery_points",
        "target": "peco:has_port",
        "kind": "nested",
        "nested_type": "peco:Electric_POD",
        "nested_fields": [
            {"source": "id", "target": "dct:identifier", "required": True}
        ],
    })
    assert fm.kind == "nested"
    assert len(fm.nested_fields) == 1
    assert fm.nested_fields[0].required is True
