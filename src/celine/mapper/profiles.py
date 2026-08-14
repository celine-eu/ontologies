"""Ontology profiles: the artifacts needed to validate a mapped graph, by name
and version.

A **profile** is one vocabulary at one version, packaged as four artifacts:

======================  ================================================
``ontology.ttl``        the vocabulary itself, merged into the data graph
``shapes.ttl``          the SHACL profile validated against
``context.jsonld``      the JSON-LD ``@context`` documents are built with
``schema.json``         the JSON Schema documents are checked against
======================  ================================================

The names are deliberately vocabulary-neutral. In this repository's ``specs/``
tree the same four files are called ``celine.ttl``, ``celine.shacl.ttl``,
``celine.jsonld`` and ``celine.schema.json``; the wheel renames them on the way
in (see ``force-include`` in ``pyproject.toml``). CELINE is one profile, not the
shape of the concept — a mapping spec already spans SOSA, SEAS, SAREF and
others, and a second profile should be droppable into ``profiles/<name>/<version>/``
without a naming exception carved out for it.

**Why this module exists at all.** ``graph.py`` used to resolve its artifacts by
walking ``__file__`` upwards to ``specs/current``, which inside an installed
environment is ``<site-packages>/specs/current`` — a directory that cannot exist.
Every installed consumer failed, and the failure surfaced as a
``FileNotFoundError`` at construction rather than as anything naming the real
problem. Resolution here goes through ``importlib.resources``, exactly as
``registry.py`` already does for ``open-repository.yaml``, so a checkout and a
wheel behave the same.

**Why versions are plural.** A dataset pins the ontology version its mapping was
written against. A newer release must not retroactively decide that a dataset
stopped conforming — upgrading is a deliberate act, not something a deployment
does to its own catalogue overnight. That only works if more than the newest
version is reachable, so the wheel carries a window of them.
"""
from __future__ import annotations

import functools
import json
import re
from dataclasses import dataclass
from importlib import resources
from pathlib import Path
from typing import Any

DEFAULT_PROFILE = "celine"

#: Packaged artifact names, and the ``specs/`` name each one comes from.
#: The second element is what a source checkout of *this* repository calls the
#: file; other profiles have no checkout tree and only ever use the first.
_ARTIFACTS = {
    "ontology": ("ontology.ttl", "celine.ttl"),
    "shapes": ("shapes.ttl", "celine.shacl.ttl"),
    "context": ("context.jsonld", "celine.jsonld"),
    "schema": ("schema.json", "celine.schema.json"),
}

# Not "profiles": this module is `celine.mapper.profiles`, and a sibling
# directory of the same name is a namespace-package portion competing with it.
# The module wins today by import-system precedence, which is not a property to
# depend on.
_PACKAGED_ROOT = "ontology_profiles"

#: Profiles that also have a source-checkout home, and where it is. Only this
#: repository's own vocabulary does: ``specs/<version>/`` is where CELINE is
#: authored, so a working tree can use a version that is not packaged yet.
_CHECKOUT_TREES = {
    DEFAULT_PROFILE: Path(__file__).resolve().parents[3] / "specs",
}

_VERSION_RE = re.compile(r"\d+")


class ProfileError(ValueError):
    """A profile could not be resolved or is incomplete."""


class ProfileNotFoundError(ProfileError, KeyError):
    """No such profile, or no such version of it."""

    def __str__(self) -> str:  # KeyError would otherwise re-quote the message
        return self.args[0] if self.args else ""


def _version_key(version: str) -> tuple[int, ...]:
    """Sort ``v0.10`` after ``v0.9``, which a string sort does not.

    Non-numeric versions sort before numeric ones rather than raising: a profile
    directory named something unexpected should not make *listing* fail.
    """
    return tuple(int(part) for part in _VERSION_RE.findall(version)) or (-1,)


@dataclass(frozen=True)
class Profile:
    """One vocabulary at one version, with its artifacts already read.

    Attributes:
        name: profile name, e.g. ``"celine"``.
        version: the *resolved* version, e.g. ``"v0.10"`` — never ``None`` and
            never ``"current"``. A report that says which shapes ran has to be
            able to name them, so resolution happens here and once.
        source: ``"packaged"``, ``"checkout"`` or ``"explicit"``. Which tree
            answered is the difference between a deployment bug and a dev box,
            and is worth being able to print.
        context: the ``@context`` block, already unwrapped from the document.
        json_schema: the parsed JSON Schema.
        shapes_ttl: SHACL profile, as Turtle text.
        ontology_ttl: the vocabulary, as Turtle text.

    Turtle is carried as text rather than as a path because a packaged artifact
    may live inside a zip, where no filesystem path exists. ``rdflib`` parses
    from ``data=`` just as happily.
    """

    name: str
    version: str
    source: str
    context: dict[str, Any]
    json_schema: dict[str, Any]
    shapes_ttl: str
    ontology_ttl: str

    def __str__(self) -> str:
        return f"{self.name} {self.version} ({self.source})"


def _packaged_root():
    return resources.files(__package__).joinpath(_PACKAGED_ROOT)


def _packaged_versions(name: str) -> list[str]:
    root = _packaged_root().joinpath(name)
    if not root.is_dir():
        return []
    return sorted((entry.name for entry in root.iterdir() if entry.is_dir()), key=_version_key)


def _checkout_versions(name: str) -> list[str]:
    tree = _CHECKOUT_TREES.get(name)
    if tree is None or not tree.is_dir():
        return []
    # `current` is a copy of the newest version, not a version. Including it
    # would make it sort as its own answer to "what can I pin to".
    return sorted(
        (entry.name for entry in tree.iterdir() if entry.is_dir() and entry.name != "current"),
        key=_version_key,
    )


def available_profiles() -> dict[str, list[str]]:
    """``{profile_name: [version, ...]}`` across packaged and checkout trees.

    Ordered oldest to newest. This is the answer to "what can I pin to", and it
    must be obtainable without unpacking the wheel by hand — the CLI's
    ``mapper profiles`` prints exactly this.
    """
    names = set()
    root = _packaged_root()
    if root.is_dir():
        names.update(entry.name for entry in root.iterdir() if entry.is_dir())
    names.update(_CHECKOUT_TREES)

    found: dict[str, list[str]] = {}
    for name in sorted(names):
        versions = sorted(
            set(_packaged_versions(name)) | set(_checkout_versions(name)),
            key=_version_key,
        )
        if versions:
            found[name] = versions
    return found


def _describe_available() -> str:
    found = available_profiles()
    if not found:
        return "no profiles are available at all, which means the wheel was built without "\
               "the force-include block in pyproject.toml"
    return "; ".join(f"{name}: {', '.join(versions)}" for name, versions in found.items())


def _read_from(directory, filenames: tuple[str, ...]) -> str | None:
    """First of ``filenames`` that exists under ``directory``, read as text."""
    for filename in filenames:
        candidate = directory.joinpath(filename)
        if candidate.is_file():
            return candidate.read_text(encoding="utf-8")
    return None


def _build(name: str, version: str, directory, source: str, filename_index: int) -> Profile:
    texts: dict[str, str] = {}
    missing: list[str] = []
    for key, names in _ARTIFACTS.items():
        # A packaged profile uses the neutral name; a checkout uses the
        # `celine.*` name it is authored under. Both are tried either way, so a
        # profile dropped into a checkout under packaged names also works.
        ordered = (names[filename_index],) + tuple(n for n in names if n != names[filename_index])
        text = _read_from(directory, ordered)
        if text is None:
            missing.append(names[filename_index])
        else:
            texts[key] = text

    if missing:
        raise ProfileError(
            f"profile {name} {version} at {directory} is incomplete: missing "
            f"{', '.join(missing)}. A profile is all four artifacts or it is not usable — "
            f"validating against a partial one reports conformance it never checked."
        )

    context_doc = json.loads(texts["context"])
    if "@context" not in context_doc:
        raise ProfileError(
            f"profile {name} {version}: {_ARTIFACTS['context'][filename_index]} has no "
            f"'@context' key"
        )

    return Profile(
        name=name,
        version=version,
        source=source,
        context=context_doc["@context"],
        json_schema=json.loads(texts["schema"]),
        shapes_ttl=texts["shapes"],
        ontology_ttl=texts["ontology"],
    )


@functools.lru_cache(maxsize=None)
def load_profile(name: str = DEFAULT_PROFILE, version: str | None = None) -> Profile:
    """Load a profile by name and version.

    Args:
        name: profile name. Defaults to CELINE, which is what every mapping spec
            in this package targets — but the parameter exists because the
            vocabulary layer is plural, and a caller pinning something else must
            not have to work around a default.
        version: an exact version such as ``"v0.10"``, or ``None`` / ``"current"``
            for the newest available. Resolution is recorded on the returned
            profile, so an unpinned run is still able to say what it ran against.

    Resolution order is **packaged first, then source checkout**. Packaged wins
    because that is what a deployment has; the checkout fallback keeps this
    repository's own tests, CLI and in-progress ontology versions working before
    a release packages them.

    Raises:
        ProfileNotFoundError: no such profile or version. The message lists what
            *is* available — the usual cause is a pin that aged out of the
            packaged window, or a typo in a mapping spec written elsewhere.
        ProfileError: the profile exists but is missing artifacts.

    The result is cached and shared. Treat it as read-only; mutating a returned
    ``context`` mutates it for every other caller.
    """
    if version in (None, "current", "latest"):
        candidates = sorted(
            set(_packaged_versions(name)) | set(_checkout_versions(name)),
            key=_version_key,
        )
        if not candidates:
            raise ProfileNotFoundError(
                f"no ontology profile named {name!r}. Available — {_describe_available()}"
            )
        version = candidates[-1]

    # Chained, not `joinpath(name, version)`: multi-argument joinpath on a
    # Traversable is 3.11+, and this package supports 3.10.
    packaged = _packaged_root().joinpath(name).joinpath(version)
    if packaged.is_dir():
        return _build(name, version, packaged, source="packaged", filename_index=0)

    tree = _CHECKOUT_TREES.get(name)
    if tree is not None:
        checkout = tree / version
        if checkout.is_dir():
            return _build(name, version, checkout, source="checkout", filename_index=1)

    raise ProfileNotFoundError(
        f"ontology profile {name!r} has no version {version!r}. Available — "
        f"{_describe_available()}. A pin older than the packaged window is not "
        f"resolvable on purpose: the shapes it names are no longer shipped."
    )


def load_profile_from_dir(directory: Path, name: str = "custom", version: str = "unversioned") -> Profile:
    """Load a profile from an arbitrary directory.

    For a profile that is neither packaged nor in a known checkout — a local
    experiment, a vendored third-party shapes set, a version being authored.
    Either naming convention works.
    """
    directory = Path(directory)
    if not directory.is_dir():
        raise ProfileNotFoundError(f"{directory} is not a directory")
    return _build(name, version, directory, source="explicit", filename_index=0)


__all__ = [
    "DEFAULT_PROFILE",
    "Profile",
    "ProfileError",
    "ProfileNotFoundError",
    "available_profiles",
    "load_profile",
    "load_profile_from_dir",
]
