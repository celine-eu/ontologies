# CELINE Ontology v0.4

**Namespace**: `https://w3id.org/celine-eu#`
**IRI**: `https://w3id.org/celine-eu`
**Version IRI**: `https://w3id.org/celine-eu/v0.4`

Adds REC flexibility commitment and settlement modelling on top of the v0.3 orchestration layer.

## Changes from v0.3

- **New class layer: Flexibility Commitment** — models a member's pledge to provide flexibility
  on one or more of their PODs, including mode (Automated / Voluntary) and direction (FlexDown / FlexUp)
- **New class: FlexibilityCredit** — kWh-denominated credit awarded upon fulfillment, grounded
  in SOSA observations for auditability
- **New class layer: Settlement** — `SettlementRun`, `CostItem`, and `RedistributionResult` model
  the full redistribution cycle: credit aggregation → monetary conversion → cost deduction → net payout per member
- **Three SKOS vocabularies** — `CommitmentMode`, `FlexibilityDirection`, `CostType` with
  built-in concepts (`Automated`, `Voluntary`, `FlexDown`, `FlexUp`, `AdminCost`, `Fee`, `Debt`)
- **SHACL shapes** added for all five new classes
- **JSON-LD context** and **JSON Schema** extended with all new terms
- No new `owl:imports` — new classes connect to existing PECO (`peco:Energy_community_member`,
  `peco:Electric_POD`) and SOSA (`sosa:Observation`) terms already in scope

## Classes

| Class | Description |
|---|---|
| `celine:CommunityContext` | Binds a PECO Energy Community with assets, datasets, simulations and commitments |
| `celine:Scenario` | Assumptions, temporal scope and configuration for simulations |
| `celine:Simulation` | Abstract simulation definition |
| `celine:SimulationRun` | Concrete execution of a Simulation under a Scenario |
| `celine:DatasetReference` | Reference to an external dataset (input or output) |
| `celine:KPIEvaluation` | Evaluation of a BIGG KPI in a Scenario or SimulationRun |
| `celine:FlexibilityCommitment` | A member's pledge to deliver flexibility on one or more PODs |
| `celine:FlexibilityCredit` | kWh credit earned by fulfilling a FlexibilityCommitment |
| `celine:SettlementRun` | Redistribution calculation for a settlement period |
| `celine:CostItem` | Named cost voice within a SettlementRun (fee, admin cost, debt) |
| `celine:RedistributionResult` | Per-member settlement outcome (credit balance, gross, deductions, net) |

## Flexibility data flow

```
peco:Energy_community_member
  │
  ├─ committedBy ←── FlexibilityCommitment ──► onPOD ──► peco:Electric_POD
  │                        │ hasCommitmentMode: Automated | Voluntary
  │                        │ hasFlexibilityDirection: FlexDown | FlexUp
  │                        │ targetFlexibility: xsd:decimal (kWh)
  │                        │ hasTimeInterval: time:Interval
  │                        │
  │                        └─ generatesCredit ──► FlexibilityCredit
  │                                                    │ creditAmount: xsd:decimal (kWh)
  │                                                    └─ evidencedBy ──► sosa:Observation
  │
  └─ resultFor ←── RedistributionResult ◄── hasRedistributionResult ──┐
                        │ creditBalance  (kWh)                         │
                        │ grossAmount    (currency)              SettlementRun
                        │ costDeduction  (currency)                    │ conversionRate (€/kWh)
                        └─ netAmount     (currency)                    │ currency (ISO 4217)
                                                                       └─ hasCostItem ──► CostItem
                                                                                              │ hasCostType: AdminCost | Fee | Debt
                                                                                              └─ costAmount (currency)
```

## Imports

- PECO (`https://purl.org/peco/peco-core`)
- SAREF core v3.1.1 + SAREF4ENER v1.2.1 (ETSI, versioned)
- SOSA (W3C `w3c/sdw@dee1bdd3c3`)
- BIGG ontology + bigg4kpi (`BeeGroup-cimne/biggontology@776e245668`)
