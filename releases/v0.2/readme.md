# CELINE Ontology v0.2

**Namespace**: `https://w3id.org/celine/ontology#`

**IRI**: `https://w3id.org/celine/ontology#CELINEOntology`

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
