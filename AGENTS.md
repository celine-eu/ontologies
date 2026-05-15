# AGENTS.md — celine-ontologies

## Repository purpose

CLI and support libraries for the CELINE ontology: versioned Turtle/JSON-LD/SHACL
specs, WIDOCO documentation generation, and a declarative YAML-to-RDF mapper.

## Repository layout

```
specs/
  v0.1/ .. v0.6/        # versioned ontology specs
    celine.ttl           # OWL/Turtle — the source of truth
    celine.jsonld        # JSON-LD context + graph summary
    celine.shacl.ttl     # SHACL shapes profile
    celine.schema.json   # JSON Schema for JSON-LD validation
    README.md            # human-readable changelog + classes table
    widoco.conf          # WIDOCO configuration (abstract, intro, description, citeAs)
    sections/            # custom WIDOCO HTML section overrides
      references-en.html
  current/               # symlink-like copy of the latest version (auto-synced)

releases/                # WIDOCO-generated HTML output (gitignored, built locally)

src/celine/
  ontologies/            # CLI: fetch, analyze, tree — entry point: main.py
  mapper/                # declarative YAML→RDF mapper engine
    specs/               # mapping spec YAML files (rec_member, rec_asset, etc.)
    cli.py               # mapper sub-commands: validate-spec, map, shacl-check, inspect
    engine.py            # mapping engine core
    spec.py              # MappingSpec loader and validation
    graph.py             # RDF graph builder
    output_mapper.py     # output format handling

tests/mapper/            # pytest tests for the mapper

data/ontologies/         # fetched external ontology files + analysis output
```

## Creating a new ontology version

### 1. Copy the previous version

```sh
cp -r specs/v0.5 specs/v0.6
```

### 2. Edit `celine.ttl`

This is the source of truth. All other files derive from it.

- Bump `owl:versionIRI` to the new version.
- Update `owl:priorVersion` to point to the previous.
- Update `owl:versionInfo` (e.g. `"0.6.0"`).
- Update `dct:modified` to today's date.
- Update the ontology-level `rdfs:comment` to describe what changed.
- Add new classes, properties, SKOS schemes as needed.
- Do **not** add new `owl:imports` without a design decision — external
  alignment uses `skos:closeMatch` / `rdfs:seeAlso` only.

### 3. Update `celine.shacl.ttl`

- Update the profile version comment at the top.
- Add shapes for new SKOS concept schemes (follow the existing
  `*SchemeShape` + `*ConceptShape` SPARQL-target pattern).
- Add `sh:property` entries to existing shapes if new optional properties
  land on existing classes (e.g. adding a property to `CommunityContextShape`).
- New class shapes are optional — the v0.6 pattern defers full class shapes
  to a later pass after the TBox is reviewed.

### 4. Update `celine.jsonld`

- Add new prefixes to `@context` if needed.
- Add `@context` term mappings for new properties (object props get
  `"@type": "@id"`, datatype props get their XSD type or are bare strings).
- Add `@graph` entries for new classes, properties, SKOS concepts.
- Update the ontology description in `@graph[0]`.

### 5. Update `celine.schema.json`

- Bump `$id` to the new version.
- Add `$defs` for new node types (follow the `allOf: [NodeBase, ...]` pattern).
- Add new `$defs` to the `Node.anyOf` union.
- Add new optional properties to existing `$defs` where needed.

### 6. Update `README.md`

- Update version header, IRI, intro paragraph.
- Add a "Changes from vN-1" section mirroring the previous version's style.
- Update the Classes table with new entries.
- Update the "Deferred" section — move items out when implemented.
- Include migration notes for downstream consumers.

### 7. Update `widoco.conf`

- Bump `thisVersionURI`, `previousVersionURI`, `publishedDate`.
- Update `abstract`, `introduction`, `description` to reflect new content.
- Update `citeAs` with the new version number.

If no `widoco.conf` exists (v0.4/v0.5 lost it), create one — WIDOCO falls
back to placeholder text without it.

### 8. Update `sections/references-en.html`

Add references for any newly aligned external standards. This file is
overlaid on top of the WIDOCO-generated output by the taskfile.

### 9. Update `CHANGELOG.md`

Add an "Ontology vX.Y" section at the top with features and deferred items.

### 10. Verify

```sh
# Parse turtle
uv run --extra mapper python -c \
  "from rdflib import Graph; g = Graph(); g.parse('specs/v0.6/celine.ttl'); print(len(g), 'triples')"

# SHACL validation
uv run --extra mapper python -c \
  "from pyshacl import validate; from rdflib import Graph; \
   d = Graph(); d.parse('specs/v0.6/celine.ttl'); \
   s = Graph(); s.parse('specs/v0.6/celine.shacl.ttl'); \
   ok, _, t = validate(d, shacl_graph=s, inference='none'); print('OK' if ok else t)"

# JSON-LD / JSON Schema parse
python -c "import json; json.load(open('specs/v0.6/celine.jsonld')); print('jsonld ok')"
python -c "import json; json.load(open('specs/v0.6/celine.schema.json')); print('schema ok')"
```

### 11. Generate WIDOCO docs and preview

```sh
task widoco:docs -- v0.6
task widoco:serve -- v0.6    # http://0.0.0.0:9902/
```

### 12. Release

```sh
task release:ontology        # copies to specs/current, tags, pushes
```

## Python codebase

### Package manager

Uses `uv` with `hatchling` build backend. Source layout: `src/celine/`.

```sh
uv sync                       # install all deps
uv sync --extra mapper        # include rdflib + pyshacl
uv sync --extra cli           # include typer + httpx + rdflib
uv sync --extra all           # everything
```

### Two subpackages

- **`celine.ontologies`** — CLI for fetching, analyzing, and visualizing
  external ontologies referenced in `open-repository.yaml`. Entry point:
  `celine-ontologies` (defined in `pyproject.toml [project.scripts]`).
- **`celine.mapper`** — declarative YAML-to-RDF mapping engine. Mapping
  specs live in `src/celine/mapper/specs/*.yaml`. Each spec maps a data
  source (e.g. rec-registry member, asset, delivery point) to an RDF target
  type using field-level rules.

### CLI commands

```sh
celine-ontologies fetch       # download ontologies from open-repository.yaml
celine-ontologies analyze     # build ontology dependency graph
celine-ontologies tree        # print ontology class tree
celine-ontologies mapper validate-spec <spec.yaml>
celine-ontologies mapper map <spec.yaml> <data.json>
celine-ontologies mapper shacl-check <spec.yaml> <data.json>
celine-ontologies mapper inspect <spec.yaml>
```

### Mapper specs

YAML files in `src/celine/mapper/specs/` define declarative mappings:

```yaml
version: "1"
target_type: "peco:Energy_community_member"
id_template: "https://w3id.org/celine/member/{key}"
fields:
  - source: role
    target: "celine:hasMemberRole"
    kind: iri
```

When adding new ontology terms that map to rec-registry fields, update the
corresponding mapper spec to use the new CELINE property IRIs.

### Tests

```sh
uv run pytest tests/          # run all tests
```

Tests live in `tests/mapper/`. Follow the existing pattern: `test_spec.py`,
`test_engine.py`, `test_graph.py`, `test_output_mapper.py`.

### Release (PyPI)

```sh
task release                  # semantic-release version bump + push
```

Triggered by conventional commits (`feat:`, `fix:`, `chore:`). The GitHub
`release.yaml` workflow builds and publishes to PyPI on tag push.

## Design constraints

- The ontology is a **lightweight orchestration profile** — it coordinates
  PECO, SAREF, SOSA, CIM without redefining their domain semantics.
- External alignment uses `skos:closeMatch` / `rdfs:seeAlso` only — **no
  `owl:imports`** beyond the four already present (PECO, SAREF, SAREF4ENER, SOSA).
- Italian regulatory terms appear in `rdfs:comment` only — never in IRIs or labels.
- Asset technical attributes live in the rec-registry, not the ontology.
  The bridge is `celine:hasLocalIdentifier`.
- SKOS ConceptSchemes are the pattern for all closed enumerations.
- Concept IRIs use a category prefix to avoid collision (e.g. `RoleConsumer`,
  `StatusActive`, `ScopeCommunity`, `MethodTotal`, `RequestOpen`).
