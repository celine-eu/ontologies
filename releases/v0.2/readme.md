# CELINE Ontology v0.2

**Namespace**: `https://w3id.org/celine-eu#`

**IRI**: `https://w3id.org/celine-eu`

Major redesign. Replaced broad domain subclassing with a **thin orchestration layer** that connects established standards without redefining their semantics. Introduced the simulation/scenario model and PECO integration.

## Changes from v0.1

- Dropped all direct subclasses (EnergyCommunity, Prosumer, Asset, Meter, TimeSeries, Observation, Tariff, CO2Factor, FlexibilityEvent, Forecast, EnergyKPI)
- New orchestration classes referencing external standards via object properties instead of subclassing
- Replaced SEAS and SAREF4CITY imports with PECO and BIGG
- Namespace moved from `https://celine-eu.github.io/ontologies/celine#` to `https://w3id.org/celine/ontology#`

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
- SOSA (W3C, via `refs/heads/gh-pages` — unstable ref, fixed in v0.3)
- BIGG ontology + bigg4kpi (via `refs/heads/main` — unstable ref, fixed in v0.3)

## Corrected 2026-09-03

**This version was released under a namespace that never resolved.** It minted its terms
in `https://w3id.org/celine/ontology#` and named the ontology itself
`https://w3id.org/celine/ontology#CELINEOntology` — a fragment, used as the document base,
which WIDOCO then turned into the malformed `…#CELINEOntology#` in the RDF/XML. No
`celine` namespace was ever registered on w3id.org, so every term IRI in this release
answered 404, and v0.3 had already renamed the namespace to `https://w3id.org/celine-eu#`
without anything going back to fix v0.2.

The artifacts have been rewritten in place to the namespace this ontology has used since
v0.3, and `owl:versionIRI <https://w3id.org/celine-eu/v0.2>` has been added — without it
this release and the current one would both claim `https://w3id.org/celine-eu` with
nothing to tell them apart.

**Only the identifiers changed.** No term was added, removed or redefined, and the
`owl:imports` set is untouched. The documentation HTML was not regenerated: this version
has no `widoco.conf`, and WIDOCO falls back to placeholder prose rather than failing, so
regenerating would have replaced a historical document with a worse one.
