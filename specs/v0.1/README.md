# CELINE Ontology v0.1

**Namespace**: `https://celine-eu.github.io/ontologies/celine#`
**IRI**: `https://celine-eu.github.io/ontologies/celine/`

Initial release. Broad domain coverage aligned with SAREF, SAREF4ENER, SAREF4CITY, SOSA/SSN, SEAS, BIGG and EM-KPI via direct subclassing.

## Classes

| Class | Parent |
|---|---|
| `celine:EnergyCommunity` | `s4city:Community` |
| `celine:Prosumer` | `s4city:CityObject` |
| `celine:Asset` | `saref:Device` |
| `celine:Meter` | `s4ener:EnergyMeter` |
| `celine:TimeSeries` | `bigg:TimeSeriesList` |
| `celine:Observation` | `sosa:Observation` |
| `celine:Tariff` | `bigg:Tariff` |
| `celine:CO2Factor` | `bigg:CO2EmissionsFactor` |
| `celine:FlexibilityEvent` | `seas:DemandResponseEvent` |
| `celine:Forecast` | `seas:Forecast` |
| `celine:EnergyKPI` | `bigg4kpi:KPIAssessment`, `emkpi:EnergyPerformanceIndicator` |

## Imports

- SAREF core + SAREF4ENER + SAREF4CITY (ETSI)
- SOSA/SSN (W3C)
- SEAS (via `https://w3id.org/seas/`)
