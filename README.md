# CELINE Ontology

Semantic artifacts and mapping tools for the CELINE project, supporting:

- semantic interoperability across datasets
- Digital Twins (WP3)
- Demonstrators, KPIs, and evaluation (WP5)
- mapping from tabular data to RDF / JSON-LD

The CELINE ontology is a **unified ontology profile** — not a standalone domain ontology — that connects PECO, SAREF, SOSA, BIGG and EM-KPI into a coherent semantic target for the CELINE ecosystem.

**Namespace**: `https://w3id.org/celine#`
**Documentation**: <https://celine-eu.github.io/ontologies/>

---

## Repository structure

```
specs/          Ontology source artifacts (versioned)
  current/      → symlink to latest version
  v0.3/
    celine.ttl           OWL/RDF definition (Turtle)
    celine.shacl.ttl     SHACL validation shapes
    celine.jsonld        JSON-LD context
    celine.schema.json   JSON Schema for API validation

releases/       Generated WIDOCO HTML documentation (versioned)
  current/      → symlink to latest version
  v0.3/         index-en.html + supporting assets

src/            Python package (celine-ontologies)
  celine/
    mapper/     Declarative data→RDF mapping engine
    ontologies/ Ontology management CLI
```

---

## Ontology artifacts

| Artifact | Description |
|---|---|
| [celine.ttl](specs/current/celine.ttl) | Formal OWL/RDF definition |
| [celine.shacl.ttl](specs/current/celine.shacl.ttl) | SHACL shapes for semantic validation |
| [celine.jsonld](specs/current/celine.jsonld) | JSON-LD `@context` for APIs and pipelines |
| [celine.schema.json](specs/current/celine.schema.json) | JSON Schema for API-level payload validation |

---

## Python package

```bash
# Mapper API only (OutputMapper, CelineGraphBuilder)
pip install celine-ontologies[mapper]

# Ontology management CLI (fetch, analyze, tree)
pip install celine-ontologies[cli]

# Everything
pip install celine-ontologies[all]
```

### Mapper usage

```python
from pathlib import Path
from celine.mapper import OutputMapper

mapper = OutputMapper.from_yaml_path(
    Path("src/celine/mapper/specs/obs_rec_energy.yaml"),
    context={"community_key": "it-folgaria"},
)
nodes = mapper.map_many(rows)
```

### CLI

```bash
# Validate a mapping spec
celine-ontologies mapper validate-spec path/to/spec.yaml

# Map data to JSON-LD
celine-ontologies mapper map spec.yaml input.json

# Map + SHACL validation (requires [mapper])
celine-ontologies mapper shacl-check spec.yaml input.json

# Ontology utilities
celine-ontologies fetch
celine-ontologies analyze
celine-ontologies tree
```

---

## How the semantic stack fits together

```
Tabular data
  ↓  mapping spec (YAML)
JSON-LD  ←  celine.jsonld context
  ↓  celine.schema.json
JSON Schema validation
  ↓  RDF expansion
SHACL validation  ←  celine.shacl.ttl
  ↓
CELINE Knowledge Graph / Digital Twin
```

---

## Releasing a new version

```bash
# 1. Add specs/vX.X/ with the new ontology artifacts

# 2. Update the specs/current symlink and tag
task release:ontology

# 3. Generate WIDOCO HTML docs locally (requires Docker)
task docs:widoco           # latest version
task docs:widoco -- vX.X  # specific version
```

WIDOCO docs are also generated automatically in CI on every push that changes a `specs/v*/celine.ttl`.

---

## Design principles

- **Standards first**: reuse ETSI SAREF, W3C SOSA/SSN, BIGG, EM-KPI
- **Thin CELINE layer**: only project-specific glue concepts are defined here
- **Modular & versionable**: `specs/` and `releases/` evolve independently
- **Tool-friendly**: compatible with rdflib, JSON-LD processors, SHACL engines
