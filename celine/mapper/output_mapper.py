"""OutputMapper: thin adapter satisfying the digital-twin output_mapper.map() contract."""
from __future__ import annotations

from pathlib import Path
from typing import Any

from celine.mapper.engine import MappingEngine
from celine.mapper.spec import MappingSpec, MappingSpecLoader


class OutputMapper:
    """Maps a single input dict to a JSON-LD node dict.

    Designed to be instantiated as a **module-level singleton** and referenced by the
    digital-twin ``ValueFetcherSpec.output_mapper`` field as ``"module:attr"``.  The
    digital-twin executor calls ``output_mapper.map(item)`` for each row in the result.

    Example (in a domain mappers.py)::

        from pathlib import Path
        from celine.mapper import OutputMapper

        rec_energy_mapper = OutputMapper.from_yaml_path(
            Path(__file__).parent / "specs" / "obs_rec_energy.yaml",
            context={"community_key": "it-folgaria"},
        )

    Args:
        spec: Parsed MappingSpec.
        context: Caller-supplied variables (e.g. EntityInfo.metadata) injected
                 into id_template alongside row fields.
        base_uri: IRI prefix for generated node identifiers.
    """

    def __init__(
        self,
        spec: MappingSpec,
        context: dict[str, Any] | None = None,
        base_uri: str = "https://w3id.org/celine/",
    ) -> None:
        self._engine = MappingEngine(spec=spec, context=context, base_uri=base_uri)

    @classmethod
    def from_yaml_path(
        cls,
        path: Path,
        context: dict[str, Any] | None = None,
        base_uri: str = "https://w3id.org/celine/",
    ) -> "OutputMapper":
        """Construct from a MappingSpec YAML file."""
        spec = MappingSpecLoader().load(path)
        return cls(spec=spec, context=context, base_uri=base_uri)

    def map(self, row: dict[str, Any]) -> dict[str, Any]:
        """Map a single input row to a JSON-LD node dict.

        This is the method called by the digital-twin executor per row.
        """
        return self._engine.map_one(row)

    def map_many(self, rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Batch variant used by the CLI and tests."""
        return self._engine.map_many(rows)
