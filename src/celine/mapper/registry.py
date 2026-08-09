"""The vocabulary registry: which ontologies CELINE supports, and how to expand
their CURIEs.

Read from the packaged ``open-repository.yaml`` via ``importlib.resources``, so
this works identically from a source checkout and an installed wheel. Everything
else in this repo that reaches for a file walks ``__file__`` upwards and breaks
the moment it is installed — see ``graph.py``'s defaults, which do exactly that
and are documented as source-checkout-only.
"""
from __future__ import annotations

import functools
from importlib import resources
from pathlib import Path
from typing import Any

import yaml

_REGISTRY_RESOURCE = "open-repository.yaml"


class PrefixError(KeyError):
    """A CURIE prefix is not declared in the registry."""


@functools.lru_cache(maxsize=1)
def load_registry() -> dict[str, Any]:
    """Parse the vocabulary registry.

    Two locations, because the file has two homes and only one of them is a
    package. Canonically it lives at the repo root, where it is edited and
    published; ``force-include`` copies it into ``celine/mapper/`` when the wheel
    is built. So an installed consumer finds the packaged copy, and a source
    checkout — tests, the CLI, anything run from this repo — falls back to the
    root. There is still exactly one file under version control.
    """
    packaged = resources.files(__package__).joinpath(_REGISTRY_RESOURCE)
    if packaged.is_file():
        return yaml.safe_load(packaged.read_text(encoding="utf-8")) or {}

    source_checkout = Path(__file__).resolve().parents[3] / _REGISTRY_RESOURCE
    if source_checkout.is_file():
        return yaml.safe_load(source_checkout.read_text(encoding="utf-8")) or {}

    raise FileNotFoundError(
        f"{_REGISTRY_RESOURCE} found neither in the package ({packaged}) nor at "
        f"the repo root ({source_checkout}). In an installed environment this "
        f"means the wheel was built without the force-include in pyproject.toml."
    )


@functools.lru_cache(maxsize=1)
def prefix_map() -> dict[str, str]:
    """``{prefix: namespace}`` across the whole registry.

    Merges the two places a prefix can be declared. Domain ontologies carry
    theirs on their `ontologies:` entry, beside the keywords and license that
    describe them; base vocabularies (``xsd``, ``rdf``, ``dct`` …) sit in the
    top-level ``prefixes:`` map, because a homepage and a keyword list say
    nothing useful about ``xsd`` and a consumer still has to resolve it.
    """
    registry = load_registry()
    mapping: dict[str, str] = {
        entry["prefix"]: entry["namespace"]
        for entry in registry.get("ontologies") or []
        if entry.get("prefix") and entry.get("namespace")
    }
    mapping.update(registry.get("prefixes") or {})
    return mapping


def expand(curie: str) -> str:
    """Expand a CURIE to an absolute IRI.

    Absolute IRIs pass through unchanged, so callers can mix the two forms the
    way mapping specs do — ``sosa:resultTime`` and
    ``https://w3id.org/celine/property/self-consumption-kw`` both appear as
    ``target`` values.

    Raises:
        PrefixError: the prefix is not in the registry. Deliberately an error
            rather than returning the CURIE untouched: an unexpanded CURIE in a
            served JSON-LD context is not a smaller failure than a missing one,
            it is the same failure discovered by the consumer instead.
    """
    if "://" in curie:
        return curie
    prefix, sep, local = curie.partition(":")
    if not sep:
        return curie
    try:
        namespace = prefix_map()[prefix]
    except KeyError as exc:
        raise PrefixError(
            f"prefix {prefix!r} (in {curie!r}) is not declared in "
            f"{_REGISTRY_RESOURCE}. Add it to the ontology's entry, or to the "
            f"top-level `prefixes:` map if it is a base vocabulary."
        ) from exc
    return f"{namespace}{local}"
