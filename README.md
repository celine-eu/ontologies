# CELINE Ontology

Semantic artifacts and mapping tools for the CELINE project, supporting:

- semantic interoperability across datasets
- Digital Twins (WP3)
- Demonstrators, KPIs, and evaluation (WP5)
- mapping from tabular data to RDF / JSON-LD

The CELINE ontology is a **unified ontology profile** — not a standalone domain ontology — that connects PECO, SAREF, SOSA/SSN into a coherent semantic target for the CELINE ecosystem. Since v0.5, KPI semantics are defined natively via a generic `KPIDefinition` / `KPICatalog` layer, with alignment to external vocabularies expressed through SKOS annotations rather than OWL imports.

**Namespace**: `https://w3id.org/celine-eu#`

**Documentation**: <https://celine-eu.github.io/ontologies/>

---

## Repository structure

```
specs/          Ontology source artifacts (versioned)
  current/      → latest version (v0.5)
  v0.5/
    celine.ttl           OWL/RDF definition (Turtle)
    celine.shacl.ttl     SHACL validation shapes
    celine.jsonld        JSON-LD context
    celine.schema.json   JSON Schema for API validation
    examples/            JSON-LD instance data examples

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

### Ontology profiles

A **profile** is one vocabulary at one version — the four artifacts above, addressed by
name and version rather than by path:

```python
from celine.mapper import GraphBuilder, MappingSpecLoader, available_profiles

available_profiles()          # {'celine': ['v0.8', 'v0.9', 'v0.10']}

spec = MappingSpecLoader().load_by_name("obs_rec_energy")
builder = GraphBuilder.for_spec(spec)          # validates against the spec's pin
builder.profile.version                        # 'v0.10'

GraphBuilder(profile="celine", version="v0.8") # a deliberate cross-version check
```

The wheel ships the **last three** spec versions, so a mapping pinned to an older one
still resolves and a cold start reaches no network. `CelineGraphBuilder` remains as an
alias defaulting to the CELINE profile.

A mapping spec declares its pin:

```yaml
profile:
  name: celine
  version: v0.10
```

Pinning is the point: a dataset asserts conformance against the ontology version its
mapping was written for, and a later release must not decide retroactively that it
stopped conforming. An unpinned spec resolves to the newest packaged version and every
report says which version actually ran, so the two cases stay distinguishable.

A pin outside the packaged window fails loudly and names what is available. That is the
cost of the three-version policy, and it is deliberate — silently validating against
different shapes than the ones claimed is worse.

### CLI

```bash
# What can a spec pin to?
celine-ontologies mapper profiles

# Validate a mapping spec
celine-ontologies mapper validate-spec path/to/spec.yaml

# Map data to JSON-LD
celine-ontologies mapper map spec.yaml input.json

# Map + SHACL validation (requires [mapper])
celine-ontologies mapper shacl-check spec.yaml input.json

# ...against a version other than the spec's pin — "would this still conform?"
celine-ontologies mapper shacl-check spec.yaml input.json --profile-version v0.9

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

- **Standards first**: reuse ETSI SAREF, W3C SOSA/SSN, PECO for domain semantics
- **Alignment via SKOS**: external KPI vocabularies (BIGG, SAREF4CITY) are referenced through `skos:closeMatch` / `skos:relatedMatch` annotations, not OWL imports
- **Thin CELINE layer**: only project-specific glue concepts are defined here
- **Modular & versionable**: `specs/` and `releases/` evolve independently
- **Tool-friendly**: compatible with rdflib, JSON-LD processors, SHACL engines
