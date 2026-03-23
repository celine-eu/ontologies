# CELINE Ontology v0.3

**Namespace**: `https://w3id.org/celine-eu#`
**IRI**: `https://w3id.org/celine-eu`
**Version IRI**: `https://w3id.org/celine-eu/v0.3`

Consolidation release. Same conceptual model as v0.2, focused on publication quality: streamlined IRI, stable import refs, documentation annotations, and proper ontology metadata.

## Changes from v0.2

- **IRI simplified**: `https://w3id.org/celine-eu/ontology#` → `https://w3id.org/celine-eu#` (removes the `/ontology` subpath)
- **Stable import refs**: GitHub `refs/heads/` replaced with pinned commit SHAs
  - `w3c/sdw` → `dee1bdd3c3`
  - `BeeGroup-cimne/biggontology` → `776e245668`
- **`skos:example`** added to every class with a realistic Turtle snippet
- **`rdfs:isDefinedBy`** added to every class and property, pointing to `<https://w3id.org/celine-eu>`
- **Ontology metadata** added: `owl:versionIRI`, `owl:priorVersion`, `owl:versionInfo`, `dct:created`, `vann:preferredNamespacePrefix`, `vann:preferredNamespaceUri`

## Classes

| Class | Description |
|---|---|
| `celine:CommunityContext` | Binds a PECO Energy Community with assets, datasets and simulations |
| `celine:Scenario` | Assumptions, temporal scope and configuration for simulations |
| `celine:Simulation` | Abstract simulation definition |
| `celine:SimulationRun` | Concrete execution of a Simulation under a Scenario |
| `celine:DatasetReference` | Reference to an external dataset (input or output) |
| `celine:KPIEvaluation` | Evaluation of a BIGG KPI in a Scenario or SimulationRun |

## Imports

- PECO (`https://purl.org/peco/peco-core`)
- SAREF core v3.1.1 + SAREF4ENER v1.2.1 (ETSI, versioned)
- SOSA (W3C `w3c/sdw@dee1bdd3c3`)
- BIGG ontology + bigg4kpi (`BeeGroup-cimne/biggontology@776e245668`)
