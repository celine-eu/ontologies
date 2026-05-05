# CELINE Ontology v0.5

**Namespace**: `https://w3id.org/celine-eu#`
**IRI**: `https://w3id.org/celine-eu`
**Version IRI**: `https://w3id.org/celine-eu/v0.5`

Introduces a generic, REC-centric KPI container and removes direct BIGG/BIGG4KPI imports.
KPI alignment is now expressed via SKOS mapping annotations rather than OWL imports.

## Changes from v0.4

- **New class: KPIDefinition** — typed KPI definition independent of evaluation, with name,
  description, optional formula, unit of measure, scope type, calculation method, and temporal
  granularity. Dual-typed as `owl:Class` and `skos:Concept` when used in the KPI catalog.
- **Modified class: KPIEvaluation** — now references a `celine:KPIDefinition` via
  `celine:hasKPIDefinition` (mandatory), replacing the previous `celine:evaluatesKPI` →
  `bigg:KPI` link. New mandatory properties: `hasKPIValue`, `hasEvaluationTimeInterval`,
  `hasEvaluatedScope`. Optional provenance via `hasInputObservation` and
  `hasInputKPIEvaluation` for derived KPIs.
- **Removed: BIGG/BIGG4KPI imports** — the two `owl:imports` targeting BIGG ontology and
  bigg4kpi extension are removed. The `bigg:` and `bigg4kpi:` prefixes are retained for
  SKOS alignment annotations.
- **Removed: `celine:evaluatesKPI`** — replaced by `celine:hasKPIDefinition`.
- **Four new SKOS concept schemes** — `KPIScope` (Community, Member, POD, Asset, Building,
  Other), `KPICalculationMethod` (Total, Average, Instantaneous, Ratio, Maximum, Minimum,
  Derived, Other), `KPITemporalGranularity` (Realtime, Hourly, Daily, Weekly, Monthly,
  Quarterly, Yearly, Period), `UnitOfMeasure` (KilowattHour, Kilowatt, Euro, Dimensionless)
- **KPI Catalog** — `celine:KPICatalog` SKOS concept scheme with 11 initial REC-relevant KPI
  definitions (SelfConsumptionRate, SelfSufficiencyRate, SharedEnergy,
  SharedEnergyMemberShare, IncentiveAccrued, IncentiveMemberShare, WithdrawnEnergy,
  FedInEnergy, LocalGenerationEnergy, PeakReductionAchieved, FlexibilityActivated)
- **SKOS alignment annotations** — class-level `skos:closeMatch` toward
  `s4city:KeyPerformanceIndicator`, `s4city:KeyPerformanceIndicatorAssessment`,
  `bigg4kpi:KPIAssessment`, and `bigg4kpi:BuildingKeyPerformanceIndicator`.
  Individual catalog entries note pending SCPS alignment.
- **SHACL shapes** — new `KPIDefinitionShape`, updated `KPIEvaluationShape`, concept scheme
  validation shapes for all four new SKOS schemes. BIGG class targets removed.
- **JSON-LD context** — BIGG prefix and `evaluatesKPI` mapping removed. New terms added for
  all KPI properties and catalog entries.

## Classes

| Class | Description |
|---|---|
| `celine:CommunityContext` | Binds a PECO Energy Community with assets, datasets, simulations and commitments |
| `celine:Scenario` | Assumptions, temporal scope and configuration for simulations |
| `celine:Simulation` | Abstract simulation definition |
| `celine:SimulationRun` | Concrete execution of a Simulation under a Scenario |
| `celine:DatasetReference` | Reference to an external dataset (input or output) |
| `celine:KPIDefinition` | **New in v0.5** — Typed KPI definition with scope, method, granularity, and unit |
| `celine:KPIEvaluation` | **Modified in v0.5** — Evaluation of a KPI, now linked to a KPIDefinition |
| `celine:FlexibilityCommitment` | A member's pledge to deliver flexibility on one or more PODs |
| `celine:FlexibilityCredit` | kWh credit earned by fulfilling a FlexibilityCommitment |
| `celine:SettlementRun` | Redistribution calculation for a settlement period |
| `celine:CostItem` | Named cost voice within a SettlementRun (fee, admin cost, debt) |
| `celine:RedistributionResult` | Per-member settlement outcome (credit balance, gross, deductions, net) |
| `celine:FlexibilityEnvelope` | Declared capability of a POD (max power up/down, available energy, availability windows) |
| `celine:FlexibilityConstraint` | Operational constraints on flexibility activation (notice, duration, recovery, frequency) |

## KPI data flow

```
celine:KPIDefinition  (typed + SKOS concept in KPICatalog)
  │ hasKPIName, hasKPIDescription, hasKPIFormula
  │ hasKPIScopeType     → KPIScope (Community | Member | POD | ...)
  │ hasKPICalculationMethod → KPICalculationMethod (Total | Ratio | ...)
  │ hasKPITemporalGranularity → KPITemporalGranularity (Period | Monthly | ...)
  │ hasKPIUnit          → UnitOfMeasure (kWh | kW | EUR | Dimensionless)
  │
  └─ hasKPIDefinition ←── KPIEvaluation
                              │ hasKPIValue: xsd:decimal
                              │ hasEvaluationTimeInterval → time:Interval
                              │ hasEvaluatedScope → CommunityContext | Member | POD
                              │ hasInputObservation → sosa:Observation (optional)
                              └─ hasInputKPIEvaluation → KPIEvaluation (optional, for derived KPIs)
```

## KPI Catalog entries

| KPI | Scope | Method | Granularity | Unit |
|---|---|---|---|---|
| `SelfConsumptionRate` | Community | Ratio | Period | Dimensionless |
| `SelfSufficiencyRate` | Community | Ratio | Period | Dimensionless |
| `SharedEnergy` | Community | Total | Period | kWh |
| `SharedEnergyMemberShare` | Member | Total | Period | kWh |
| `IncentiveAccrued` | Community | Total | Period | EUR |
| `IncentiveMemberShare` | Member | Total | Period | EUR |
| `WithdrawnEnergy` | POD | Total | Period | kWh |
| `FedInEnergy` | POD | Total | Period | kWh |
| `LocalGenerationEnergy` | Community | Total | Period | kWh |
| `PeakReductionAchieved` | Community | Total | Period | kW |
| `FlexibilityActivated` | Community | Total | Period | kWh |

## Migration from v0.4

1. Replace `celine:evaluatesKPI <bigg:KPI_IRI>` with `celine:hasKPIDefinition <celine:CatalogEntry>`
2. Replace `rdf:value "..."^^xsd:decimal` with `celine:hasKPIValue "..."^^xsd:decimal`
3. Add `celine:hasEvaluationTimeInterval` and `celine:hasEvaluatedScope` (now mandatory)
4. Remove any direct references to `bigg:` or `bigg4kpi:` terms in instance data
5. Optionally add `celine:hasInputObservation` for provenance

## Imports

- PECO (`https://purl.org/peco/peco-core`)
- SAREF core v3.1.1 + SAREF4ENER v1.2.1 (ETSI, versioned)
- SOSA (W3C `w3c/sdw@dee1bdd3c3`)
