# CELINE Ontology v0.6

**Namespace**: `https://w3id.org/celine-eu#`
**IRI**: `https://w3id.org/celine-eu`
**Version IRI**: `https://w3id.org/celine-eu/v0.6`

Additively extends v0.5 with REC-registry-aligned grid topology, regulatory zones, the
GridOperator actor, a generalised ConnectionPoint superclass, and a presence-only asset
inventory. CIM alignment via `skos:closeMatch` (IEC 61968 profile); SAREF alignment via
`skos:closeMatch` only — no new `owl:imports`.

## Changes from v0.5

### New classes (15)

- **`celine:Substation`** — abstract superclass for electrical substations (`rdfs:subClassOf peco:Asset`)
- **`celine:PrimarySubstation`** — HV/MV substation (e.g. Italian cabina primaria)
- **`celine:SecondarySubstation`** — MV/LV substation (e.g. Italian cabina secondaria)
- **`celine:PowerTransformer`** — transformer within a substation
- **`celine:DistributionFeeder`** — feeder line from substation to downstream connection points
- **`celine:RegulatoryZone`** — administrative coverage area (e.g. GSE primary-substation service zone)
- **`celine:GridOperator`** — grid infrastructure operator, typically a DSO (`rdfs:subClassOf peco:Agent`)
- **`celine:ConnectionPoint`** — generalised grid connection point; `peco:Electric_POD` is declared as subclass
- **`celine:SharingGroup`** — community partition for shared self-consumption within a regulatory zone (RED II double-counting prohibition)
- **`celine:FlexibilityRequest`** — demand signal requesting members to activate flexibility
- **`celine:PVSystem`** — photovoltaic system (presence-only)
- **`celine:BatteryStorage`** — battery energy storage system (`rdfs:subClassOf peco:Energy_storage`)
- **`celine:ElectricityMeter`** — metering device
- **`celine:EVCharger`** — electric vehicle charging station
- **`celine:HeatPump`** — heat pump for heating/cooling

### New object properties — grid & assets (9)

- **`celine:hasIdentifierScheme`** — ConnectionPoint → skos:Concept (from ConnectionPointIdentifierScheme)
- **`celine:operatedBy`** — (Substation ∪ PowerTransformer ∪ DistributionFeeder) → GridOperator
- **`celine:servedBy`** — RegulatoryZone → Substation
- **`celine:inRegulatoryZone`** — (Member ∪ ConnectionPoint) → RegulatoryZone
- **`celine:hasRegulatoryZone`** — CommunityContext → RegulatoryZone
- **`celine:hasTopologyNode`** — CommunityContext → (Substation ∪ PowerTransformer ∪ DistributionFeeder)
- **`celine:hasGridOperator`** — CommunityContext → GridOperator
- **`celine:pairedWith`** — peco:Asset → peco:Asset (symmetric)
- **`celine:measures`** — ElectricityMeter → peco:Asset

### New datatype property (1)

- **`celine:hasLocalIdentifier`** — (ConnectionPoint ∪ peco:Asset) → xsd:string

### New object properties — flexibility request (5)

- **`celine:hasFlexibilityRequest`** — CommunityContext → FlexibilityRequest
- **`celine:requestedBy`** — FlexibilityRequest → peco:Agent
- **`celine:hasRequestStatus`** — FlexibilityRequest → skos:Concept (from RequestStatus)
- **`celine:resultsInCommitment`** — FlexibilityRequest → FlexibilityCommitment
- **`celine:inResponseTo`** — FlexibilityCommitment → FlexibilityRequest (inverse of resultsInCommitment)

### New datatype property — flexibility request (1)

- **`celine:requestedFlexibility`** — FlexibilityRequest → xsd:decimal (target kWh, positive)

### New object properties — member & sharing group (5)

- **`celine:hasMember`** — (CommunityContext ∪ SharingGroup) → peco:Energy_community_member (domain widened from CommunityContext to also include SharingGroup)
- **`celine:hasDeliveryPoint`** — peco:Energy_community_member → ConnectionPoint
- **`celine:hasMemberRole`** — peco:Energy_community_member → skos:Concept (from MemberRole)
- **`celine:hasMemberStatus`** — peco:Energy_community_member → skos:Concept (from MemberStatus)
- **`celine:hasPartition`** — CommunityContext → SharingGroup (inverse: `celine:partitionOf`)

### New SKOS concept schemes (4)

- **`celine:ConnectionPointIdentifierScheme`** with 6 concepts: `POD` (Italy), `CUPS` (Spain),
  `PRM` (France), `MALO` (Germany), `EAN` (Belgium/Netherlands), `MPAN` (United Kingdom)
- **`celine:MemberRole`** with 5 concepts: `RoleConsumer`, `RoleProsumer`, `RoleProducer`,
  `RoleOperator`, `RoleAdmin`
- **`celine:MemberStatus`** with 4 concepts: `StatusPending`, `StatusActive`,
  `StatusSuspended`, `StatusInactive`
- **`celine:RequestStatus`** with 5 concepts: `RequestOpen`, `RequestFulfilled`,
  `RequestPartial`, `RequestExpired`, `RequestCancelled`

### Modified

- **`peco:Electric_POD`** — declared `rdfs:subClassOf celine:ConnectionPoint`. This is the single
  statement where v0.6 reaches into PECO's namespace. Existing POD queries continue to work;
  new queries can use `ConnectionPoint` for country-portable code.
- **`celine:CommunityContext`** — gains four new optional properties: `hasRegulatoryZone`,
  `hasTopologyNode`, `hasGridOperator`, `hasFlexibilityRequest`.
- **`celine:FlexibilityCommitment`** — gains optional `inResponseTo` linking back to the
  triggering FlexibilityRequest.
- **`celine:hasFlexibilityDirection`** — domain widened from FlexibilityCommitment to
  union of FlexibilityCommitment and FlexibilityRequest.

### Alignment policy

- All CIM references use `skos:closeMatch` only — **no `owl:imports` of CIM**. Target profile: IEC 61968.
- All SAREF references use `skos:closeMatch` only — no `owl:imports` beyond what PECO already pulls in.
- Italian regulatory terms appear in `rdfs:comment` examples only — never in IRIs or labels.

### Design notes

- **Presence-only asset inventory** — asset classes carry no technical-attribute datatype
  properties. Specs (rated power, COP, panel type, etc.) live in the external rec-registry
  catalogue, looked up via `celine:hasLocalIdentifier`.
- **Open-world absence** — "no battery" = no battery instance in the graph. No inventory-complete flag.

## Deferred to future versions

- Asset technical attributes (rated_power, COP, panel_type, battery chemistry, etc.)
- Asset-type SKOS sub-classification schemes (PanelType, BatteryChemistry, ChargerType)
- Generic `Load` class — too underspecified; generic loads remain unsubclassed `peco:Asset`
- Device block (manufacturer, model, serial, MAC, firmware)
- Telemetry / time-series measurement layer
- Closed-world absence assertions (inventory-complete flag)
- SHACL shapes for the new classes

## Classes

| Class | Description |
|---|---|
| `celine:CommunityContext` | Binds a PECO Energy Community with assets, datasets, simulations and commitments |
| `celine:Scenario` | Assumptions, temporal scope and configuration for simulations |
| `celine:Simulation` | Abstract simulation definition |
| `celine:SimulationRun` | Concrete execution of a Simulation under a Scenario |
| `celine:DatasetReference` | Reference to an external dataset (input or output) |
| `celine:KPIDefinition` | Typed KPI definition with scope, method, granularity, and unit |
| `celine:KPIEvaluation` | Evaluation of a KPI, linked to a KPIDefinition |
| `celine:FlexibilityCommitment` | A member's pledge to deliver flexibility on one or more PODs |
| `celine:FlexibilityCredit` | kWh credit earned by fulfilling a FlexibilityCommitment |
| `celine:SettlementRun` | Redistribution calculation for a settlement period |
| `celine:CostItem` | Named cost voice within a SettlementRun (fee, admin cost, debt) |
| `celine:RedistributionResult` | Per-member settlement outcome (credit balance, gross, deductions, net) |
| `celine:FlexibilityEnvelope` | Declared capability of a POD (max power up/down, available energy, availability windows) |
| `celine:FlexibilityConstraint` | Operational constraints on flexibility activation (notice, duration, recovery, frequency) |
| `celine:FlexibilityRequest` | **New in v0.6** — Demand signal requesting members to activate flexibility |
| `celine:Substation` | **New in v0.6** — Abstract superclass for electrical substations |
| `celine:PrimarySubstation` | **New in v0.6** — HV/MV substation |
| `celine:SecondarySubstation` | **New in v0.6** — MV/LV substation |
| `celine:PowerTransformer` | **New in v0.6** — Transformer within a substation |
| `celine:DistributionFeeder` | **New in v0.6** — Feeder line from substation to connection points |
| `celine:RegulatoryZone` | **New in v0.6** — Administrative coverage area |
| `celine:GridOperator` | **New in v0.6** — Grid infrastructure operator (DSO) |
| `celine:ConnectionPoint` | **New in v0.6** — Generalised grid connection point (superclass of Electric_POD) |
| `celine:SharingGroup` | **New in v0.6** — Community partition for shared self-consumption within a regulatory zone |
| `celine:PVSystem` | **New in v0.6** — Photovoltaic system (presence-only) |
| `celine:BatteryStorage` | **New in v0.6** — Battery energy storage system |
| `celine:ElectricityMeter` | **New in v0.6** — Electricity metering device |
| `celine:EVCharger` | **New in v0.6** — Electric vehicle charging station |
| `celine:HeatPump` | **New in v0.6** — Heat pump |

## Grid topology

```
RegulatoryZone --servedBy--> PrimarySubstation --feeds/fed_by--> SecondarySubstation
                                                                       |
                                                                       v
                                                                DistributionFeeder
                                                                       |
                                                                       v
                                                              ConnectionPoint
                                                                  (has subclass peco:Electric_POD)
                                                                       ^
                                                                       | peco:related_to_pod
Member (peco:Energy_community_member)
   |
   | peco:owns
   v
{PVSystem, BatteryStorage, ElectricityMeter, EVCharger, HeatPump}
   ^
   | celine:measures
ElectricityMeter

GridOperator --operatedBy(inv)--> {Substation, PowerTransformer, DistributionFeeder}

CommunityContext --hasRegulatoryZone--> RegulatoryZone
CommunityContext --hasTopologyNode---> {Substation, PowerTransformer, DistributionFeeder}
CommunityContext --hasGridOperator---> GridOperator
```

## KPI data flow

```
celine:KPIDefinition  (typed + SKOS concept in KPICatalog)
  | hasKPIName, hasKPIDescription, hasKPIFormula
  | hasKPIScopeType     -> KPIScope (Community | Member | POD | ...)
  | hasKPICalculationMethod -> KPICalculationMethod (Total | Ratio | ...)
  | hasKPITemporalGranularity -> KPITemporalGranularity (Period | Monthly | ...)
  | hasKPIUnit          -> UnitOfMeasure (kWh | kW | EUR | Dimensionless)
  |
  +-- hasKPIDefinition <-- KPIEvaluation
                              | hasKPIValue: xsd:decimal
                              | hasEvaluationTimeInterval -> time:Interval
                              | hasEvaluatedScope -> CommunityContext | Member | POD
                              | hasInputObservation -> sosa:Observation (optional)
                              +-- hasInputKPIEvaluation -> KPIEvaluation (optional, for derived KPIs)
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
| `PeakReductionAchieved` | Community | Derived | Period | kW |
| `FlexibilityActivated` | Community | Total | Period | kWh |

## Migration from v0.5

1. **Additive only** — no v0.5 classes or properties are removed or retyped.
2. `peco:Electric_POD` gains `celine:ConnectionPoint` as a new superclass — strengthens but
   does not break existing data.
3. Existing instance data continues to validate against v0.5 SHACL shapes.
4. To use new classes: type grid topology as CIM-aligned CELINE classes; assert asset-type
   instances on members via `peco:owns`.
5. Use `celine:hasLocalIdentifier` on connection points and assets as the lookup key into the
   external rec-registry catalogue.

## Imports

- PECO (`https://purl.org/peco/peco-core`)
- SAREF core v3.1.1 + SAREF4ENER v1.2.1 (ETSI, versioned)
- SOSA (W3C `w3c/sdw@dee1bdd3c3`)
