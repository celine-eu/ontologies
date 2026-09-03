# CELINE Ontology v0.11

**Namespace**: `https://w3id.org/celine-eu#`
**IRI**: `https://w3id.org/celine-eu`
**Version IRI**: `https://w3id.org/celine-eu/v0.11`

Finishes the half v0.10 left open. v0.10 gave measurement a `sosa:observedProperty` that
resolves and said, in its own comment, that "the three forecast specs still do [point at dead
IRIs], and the forecast properties they need are not minted here". They are minted here — and
not as the six forecast counterparts that sentence implied. Additive: no term is removed or
retyped, and existing instance data validates unchanged.

## Changes from v0.10

### New class — `celine:Forecast`, a `sosa:Observation` subclass

The decision is a reading of SOSA rather than a stretch of it, and both definitions are in
the `sosa.ttl` this profile already imports:

- `sosa:Observation` — *"Act of carrying out an (Observation) Procedure to **estimate or
  calculate** a value of a property of a FeatureOfInterest."* A computed forecast is an
  estimate. SOSA nowhere restricts this to a physical reading.
- `sosa:Procedure` — *"A workflow, protocol, plan, **algorithm, or computational method** …
  A Procedure is **re-usable**, and might be involved in many Observations."* That is a
  forecasting model, including a foundation model, described by the standard.

`sosa:usedProcedure` carries `schema:domainIncludes sosa:Observation`, so nothing is bent.

The subclass is declared rather than left implicit for two reasons: a consumer selects
forecasts by type instead of comparing two timestamps, and one future `ObservationShape`
reaches both families.

**The consequence worth stating plainly: the six observable properties are shared between
measurement and forecast rather than doubled.** A forecast of grid import and a measurement
of grid import name the same property, so comparing forecast against actual compares like
with like — which is the whole reason anyone stores both.

### New classes and properties (8)

| Term | Type | Purpose |
|---|---|---|
| `celine:Forecast` | class, `rdfs:subClassOf sosa:Observation` | An estimate for a time later than the one it was made at |
| `celine:ForecastModel` | class, `rdfs:subClassOf sosa:Procedure` | The model that produced it, reached by `sosa:usedProcedure` |
| `celine:ForecastRun` | class | One execution of a model; forecasts sharing a run are one series |
| `celine:forecastRun` | object property | `Forecast` → `ForecastRun` |
| `celine:forecastTargetTime` | datatype property, `xsd:dateTime` | The instant the forecast is about |
| `celine:hasLowerBound` | datatype property, `xsd:decimal` | Lower end of the prediction interval |
| `celine:hasUpperBound` | datatype property, `xsd:decimal` | Upper end of the prediction interval |
| `celine:hasConfidence` | datatype property, `xsd:decimal` | The level those bounds cover, as a fraction in [0,1] |

### Why not `peco:Forecast`

PECO has a Forecast class, it is well formed, and it was the working answer until it was
costed. `peco:Forecast` requires `peco:related_to_property_of_interest` exactly once onto
`peco:Property_of_interest`, which itself requires `has_value` exactly once onto `peco:Value`,
which requires a unit node and a quantity. **One forecast row becomes three nested levels
plus a `peco:Unit` individual**, where the metering specs use a flat `qudt:hasUnit` IRI.

Every mapping spec in this project reads flat SQL rows, and the mapper only builds a nested
node from a column that already holds a dict. So the PECO shape is not reachable without
either restructuring the dbt views or extending the mapper — before a single forecast is
served. `skos:closeMatch celine:Forecast peco:Forecast` records the correspondence without
inheriting the cost.

Worth knowing what was wrong before, because it was not only the dead IRIs: the three
forecast specs put `sosa:observedProperty` on a `peco:Forecast`, whose domain is
`sosa:Observation`. Under OWL-RL that does not fail — it silently *infers* the Forecast is an
Observation. v0.11 makes the type explicit instead of leaving it to be derived by accident.

### Why `celine:forecastTargetTime` and not `sosa:phenomenonTime`

`sosa:phenomenonTime` has range `time:TemporalEntity`, so its value must be a node and a
literal will not do — the one thing that would have reintroduced the nesting this design
exists to avoid. `celine:forecastTargetTime` is the literal shortcut, and the precedent is
SOSA's own: `sosa:hasSimpleResult` stands in exactly this relation to `sosa:hasResult`. It
carries `rdfs:seeAlso sosa:phenomenonTime` and does **not** replace it — a consumer needing
an interval rather than an instant should use `sosa:phenomenonTime` directly.

`sosa:ObservationCollection` would have been the natural home for a forecast series, but it
lives in the SSN extension rather than the `sosa.ttl` imported here, and pulling it in would
be a fifth `owl:imports` — a design decision with a record, not an editing step. A shared
`celine:ForecastRun` gives the same grouping without one.

### New — `sosa:ObservableProperty` individual (1)

| Individual | Quantity kind | Reports |
|---|---|---|
| `celine:SpecificPVYield` | *none — see below* | PV energy yield normalised by installed peak power, in kWh/kWp |

**The only property in this profile with no `qudt:hasQuantityKind`, deliberately.** kWh/kWp
is energy over *power*, so `quantitykind:Energy` and `quantitykind:DimensionlessRatio` are
both false — the latter is what `celine:SelfConsumptionRatio` correctly uses, because that
one is energy over energy. `quantitykind:Time` is dimensionally right (1 kWh/kWp is one
equivalent full-load hour) but reads as a duration to any consumer who does not already know
the identity. A wrong quantity kind silently corrupts unit arithmetic; none corrupts nobody,
so the unit carries the meaning and the comment states the equivalence.

It cannot be avoided by remodelling as absolute energy: the datasets carrying it rank rooftops
that do not exist yet, so there is no plant to be absolute about.

### New prefix — WGS84 `geo:`

`geo: <http://www.w3.org/2003/01/geo/wgs84_pos#>`, for `geo:lat` and `geo:long` as
`xsd:decimal` literals. **Referenced, not imported** — the same treatment `time:` has had
since v0.5, so the import set stays at four.

This exists because `obs_pv_forecast.yaml` was putting `lat` on `peco:has_property_kind` and
`lon` on `peco:has_property_of_interest`, both *object* properties in PECO's property chain.
Coordinates belong on the feature of interest, whose type `geo:lat` names
(`geo:SpatialThing`) — not on the forecast, which would infer that a forecast is a place.

### Deferred — SHACL shapes for the new classes

`celine.shacl.ttl` gains no shape in v0.11. That is this profile's convention for a TBox that
has not been reviewed, and it is recorded rather than left as an omission.

There is a sharper reason too. The profile still carries **no shape targeting
`sosa:Observation`**, the type of every metering row and now of every forecast, so those
datasets conform because there is nothing to violate. That shape has to land *after* the
three forecast mapping specs are corrected, never before: landing it first turns every
metering and forecast conformance report red at once.

### Migration notes

- **Nothing breaks.** Additive only; v0.10 instance data validates unchanged.
- **Forecast producers** should emit `@type: celine:Forecast`, a `celine:forecastTargetTime`,
  and a `sosa:observedProperty` drawn from the seven declared individuals — not a
  `https://w3id.org/celine/property/*` constant, which is in no namespace and never resolved.
- **`celine-pipelines`** needs the forecast views to emit the columns these map from:
  `forecast_target_time`, the bound pair, `confidence`, a `model_iri` and a `run_iri`, and a
  `feature_iri` for the location where coordinates were being carried inline.
- **Consumers comparing forecast to actual** can now join on `sosa:observedProperty`
  directly, which was not possible while the two used different vocabularies.

## Changes from v0.9

### New — `sosa:ObservableProperty` individuals (6)

| Individual | Quantity kind | Reports |
|---|---|---|
| `celine:GridImportEnergy` | `quantitykind:Energy` | Energy drawn from the distribution grid over the interval (IT: *prelievo*) |
| `celine:GridExportEnergy` | `quantitykind:Energy` | Energy fed into the distribution grid over the interval (IT: *immissione*) |
| `celine:SelfConsumedEnergy` | `quantitykind:Energy` | Energy produced and consumed behind the same connection point, never reaching the grid |
| `celine:CollectivelySharedEnergy` | `quantitykind:Energy` | The incentivised CER quantity: `min(grid import, grid export)` over coincident members, per primary substation |
| `celine:VirtualConsumedEnergy` | `quantitykind:Energy` | A member's pro-rata share of collectively shared energy, allocated by contribution to community grid import |
| `celine:SelfConsumptionRatio` | `quantitykind:DimensionlessRatio` | Shared energy over grid export, per substation |

These are CELINE terms because no standard has them, not by preference. `quantitykind:Energy`
is the correct *quantity kind* for five of the six and is asserted on each, but it does not
distinguish energy drawn from the grid from energy fed into it — and that distinction is the
whole content of a REC settlement.

Their names follow the **meaning** of the dbt columns rather than the column names, which are
misleading: `total_consumption_kwh` is community *grid import*, `total_production_kwh` is
*grid export*, and `self_consumption_kwh` is *collectively shared* energy rather than any
individual's self-use.

### Why SOSA and not SAREF

`saref:Measurement` is `owl:deprecated` in SAREF core v3.2.1 — *"in favour of
saref:Observation, to generalize to observation of states and convergence with SOSA/SSN"* —
and `saref:Energy`, `saref:Power` and the unit individuals are deprecated with it. SOSA also
supplies `sosa:hasSimpleResult`, the sanctioned way to put a literal result directly on an
observation; SAREF would need an intermediate `saref:PropertyValue` node that a flat row
cannot mint. SAREF remains correct for the **device** side, and CIM for the **grid** side.

### New prefixes — QUDT

| Prefix | Namespace | Role |
|---|---|---|
| `qudt` | `http://qudt.org/schema/qudt#` | `qudt:hasQuantityKind`, `qudt:hasUnit` |
| `quantitykind` | `http://qudt.org/vocab/quantitykind/` | Values carried by data, not mapping targets |
| `unit` | `http://qudt.org/vocab/unit/` | Values carried by data, not mapping targets |

No `owl:imports` is added. QUDT supplies the unit vocabulary because nothing already present
does: `saref:isMeasuredIn` ranges over `saref:UnitOfMeasure` whose individuals are deprecated
as of SAREF core v3.2.1, and `celine:UnitOfMeasure` is a four-concept SKOS scheme that
resolves for nobody outside CELINE. An alignment from that scheme to QUDT is still owed.

### Relation to the KPI Catalog — `rdfs:seeAlso`

Four of the six quantities already have a concept in `celine:KPICatalog`, and the two families
are **not** interchangeable. A `KPIDefinition` is a period total or rate evaluated over a
`KPIScopeType` and reported through `KPIEvaluation`; an `ObservableProperty` is what a single
`sosa:Observation` measures over one interval. The pairs are linked with `rdfs:seeAlso` — not
`skos:closeMatch`, which relates concepts within SKOS vocabularies, and an `ObservableProperty`
is not a `skos:Concept` here.

| Observable property (v0.10) | KPI concept (v0.5) |
|---|---|
| `celine:GridImportEnergy` | `celine:WithdrawnEnergy` |
| `celine:GridExportEnergy` | `celine:FedInEnergy` |
| `celine:CollectivelySharedEnergy` | `celine:SharedEnergy` |
| `celine:VirtualConsumedEnergy` | `celine:SharedEnergyMemberShare` |
| `celine:SelfConsumptionRatio` | `celine:SelfConsumptionRate` |

This is why the shared-energy property is named `CollectivelySharedEnergy` and not the obvious
`SharedEnergy`: that IRI is a released KPICatalog concept, and reusing it would put two
`rdf:type`s, two conflicting `rdfs:label`@en and two definitions on one node.

`celine:SelfConsumptionRatio` and `celine:SelfConsumptionRate` are deliberately distinct and
use **different denominators** — the property divides shared energy by grid export per
substation; the KPI divides by local production at community scope. A consumer must read the
denominator from the definition rather than assume it from the name.

### New SHACL shape — `celine:DefinedTermLabelShape`

Targets every term carrying `rdfs:isDefinedBy <https://w3id.org/celine-eu>` and asserts
`sh:uniqueLang` on `rdfs:label` and `skos:prefLabel`. It exists because the first draft of
v0.10 minted `celine:SharedEnergy` twice and every existing check passed: the Turtle parsed,
the SHACL profile validated, and the test suite was green. Nothing looked at the labels.

The shape uses `sh:target [ a sh:SPARQLTarget ]`, so it requires pyshacl `advanced=True` — as
do all the pre-existing `*ConceptShape`s, which had been running vacuously.

## Changes from v0.8

### Fixed — `cim:` prefix rebound to IEC CIM100

| | Namespace |
|---|---|
| v0.8 (wrong) | `https://ontology.tno.nl/IEC_CIM/` |
| v0.9 | `http://iec.ch/TC57/CIM100#` |

TNO hosts a copy of CIM at that first URL; it is not where CIM mints its terms. Rebinding
changes the IRI that all seven `skos:closeMatch` alignments expand to, in both `celine.ttl`
and the `celine.jsonld` `@context`:

| CELINE class | CIM100 target |
|---|---|
| `celine:Substation`, `celine:PrimarySubstation`, `celine:SecondarySubstation` | `cim:Substation` |
| `celine:PowerTransformer` | `cim:PowerTransformer` |
| `celine:DistributionFeeder` | `cim:Feeder` |
| `celine:GridOperator` | `cim:Organisation` |
| `celine:ConnectionPoint` | `cim:UsagePoint` |

### Fixed — `celine:GridOperator` alignment

`cim:Company` exists in no CIM version; the alignment is now `cim:Organisation`. Note that
`cim:Operator` is a control-room *person*, not the operating company, and is not the target.

### Alignment authority

CIM is the one external vocabulary CELINE references on **documentary** rather than
resolvable authority. IEC CIM is a paid standard and every CIM namespace IRI answers
HTTP 403, so these terms are checked against the published CIM100 class documentation
(<https://zepben.github.io/evolve/docs/cim/cim100/>) rather than dereferenced. The target
profile stated in v0.6 (IEC 61968) is superseded by CIM100, which subsumes it.

## Changes from v0.7

### Fixed — SKOS top concepts (4 schemes)

Each of the four schemes now declares its entry points:

| Scheme | Top concepts |
|---|---|
| `celine:CommitmentMode` | `Automated`, `Voluntary` |
| `celine:FlexibilityDirection` | `FlexDown`, `FlexUp` |
| `celine:CostType` | `AdminCost`, `Fee`, `Debt` |
| `celine:ConstraintType` | `DurationConstraint`, `NoticeConstraint`, `RecoveryConstraint`, `FrequencyConstraint` |

The concepts already carried `skos:inScheme` **and** `skos:topConceptOf`; only the
scheme-side `skos:hasTopConcept` was missing. All four schemes are flat — there is no
`skos:broader` anywhere in the ontology — so every member is genuinely a top concept. The
shapes (`celine:CommitmentModeSchemeShape` and the three siblings) are unchanged: they were
correct, and they are what caught this.

### Modified — language tags

Labels, prefLabels, descriptions and comments in those four scheme blocks gain `@en`,
matching the nine schemes added in v0.5 and later. Untagged literals and `@en`-tagged ones
are distinct RDF terms, so consumers matching on a plain string in these four vocabularies
must now match the tagged form.

## Changes from v0.6

### New object property (1)

- **`celine:hasDataset`** — (ConnectionPoint ∪ peco:Asset) → DatasetReference. Links an asset
  or connection point to an external, self-describing datasource. Operational counterpart to
  the SimulationRun-scoped `usesDataset`/`producesDataset`.

### Modified

- **`celine:DatasetReference`** — comment updated to note that instances SHOULD declare
  conformance target (`dct:conformsTo`), format (`dct:format`), and access location
  (`dcat:accessURL` or `dct:source`) using DCAT/Dublin Core terms. Example updated with
  generic placeholder conformance URI.
- **Comment-text generalisation** — all references to "rec-registry catalogue" replaced with
  neutral "external catalogue" wording across: ontology header, `PVSystem`, `BatteryStorage`,
  `EVCharger`, `HeatPump`, `hasMemberRole`, `hasMemberStatus`, `hasDeliveryPoint`, and
  `hasLocalIdentifier` comments. No domain/range changes.

### New prefix

- **`dcat:`** (`http://www.w3.org/ns/dcat#`) — prefix-only declaration (no `owl:imports`),
  consistent with the ontology's align-by-reference discipline.

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
  properties. Specs (rated power, COP, panel type, etc.) live in an external catalogue,
  looked up via `celine:hasLocalIdentifier`.
- **Open-world absence** — "no battery" = no battery instance in the graph. No inventory-complete flag.

## Deferred to future versions

- Asset technical attributes (rated_power, COP, panel_type, battery chemistry, etc.)
- Asset-type SKOS sub-classification schemes (PanelType, BatteryChemistry, ChargerType)
- Generic `Load` class — too underspecified; generic loads remain unsubclassed `peco:Asset`
- Device block (manufacturer, model, serial, MAC, firmware)
- Closed-world absence assertions (inventory-complete flag)
- SHACL shapes for the new v0.6 classes
- **Forecast observable properties** — the three `obs_*_forecast` mapping specs still point
  `sosa:observedProperty` at undeclared `https://w3id.org/celine/property/*` IRIs. v0.10 mints
  the measured properties only; the forecast counterparts (and how a forecast differs from an
  observation in SOSA terms) are unresolved.
- **`celine:UnitOfMeasure` → QUDT alignment** — the four-concept SKOS scheme is aligned to UCUM
  and resolves for nobody outside CELINE. Now that `unit:` is registered, a `skos:closeMatch`
  from each concept to its QUDT unit is owed.
- **`sosa:Observation` shape in `celine.shacl.ttl`** — v0.10 declares the properties but adds no
  shape constraining observations that use them (one `observedProperty`, one result, a unit).

Delivered in v0.10, previously deferred:

- ~~Telemetry / time-series measurement layer~~ — the observation structure is SOSA's, with the
  six CELINE observable properties above supplying what SOSA leaves to the domain.

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

## Observable Properties

Individuals of `sosa:ObservableProperty`, all **new in v0.10**. Instance data references them
by absolute IRI in `sosa:observedProperty`.

| Individual | Quantity kind | `rdfs:seeAlso` |
|---|---|---|
| `celine:GridImportEnergy` | `quantitykind:Energy` | `celine:WithdrawnEnergy` |
| `celine:GridExportEnergy` | `quantitykind:Energy` | `celine:FedInEnergy` |
| `celine:SelfConsumedEnergy` | `quantitykind:Energy` | — |
| `celine:CollectivelySharedEnergy` | `quantitykind:Energy` | `celine:SharedEnergy` |
| `celine:VirtualConsumedEnergy` | `quantitykind:Energy` | `celine:SharedEnergyMemberShare` |
| `celine:SelfConsumptionRatio` | `quantitykind:DimensionlessRatio` | `celine:SelfConsumptionRate` |

Produced by the `obs_energy_measurement` mapping spec over the `*_measurements_*` views in
`celine-pipelines`. One quantity per row, one `sosa:Observation` per quantity:

```
sosa:Observation
  | dct:identifier            -> xsd:string   (view surrogate, md5 of the full grain)
  | sosa:resultTime           -> xsd:dateTime
  | sosa:observedProperty     -> one of the six above
  | sosa:hasSimpleResult      -> xsd:decimal
  | qudt:hasUnit              -> unit:KiloW-HR | unit:UNITLESS
  | sosa:hasFeatureOfInterest -> connection point, device, community or substation
  +-- sosa:madeBySensor       -> the meter, where the row has one
```

`observedProperty`, `hasFeatureOfInterest`, `madeBySensor` and `hasUnit` carry **absolute
IRIs** in the data, not bare keys or CURIEs. A derived JSON-LD context can only say
`"@type": "@id"`; it cannot carry a template. A column holding a bare key therefore expands to
a *relative* IRI against whatever URL the consumer fetched the context from — silently, and
differently per consumer. Emitting the full IRI upstream is what avoids that.

## Migration from v0.9

1. **Additive** — the six observable properties, the three QUDT prefixes, the `rdfs:seeAlso`
   links and one SHACL shape are added. Nothing is removed or retyped, so existing v0.9
   instance data validates unchanged against the v0.10 profile.
2. **`celine:SharedEnergy` did not change meaning.** It remains the KPICatalog concept it has
   been since v0.5. If you are recording a *measurement* of shared energy rather than a period
   KPI, the term you want is `celine:CollectivelySharedEnergy`.
3. **Enable pyshacl `advanced=True`.** Any consumer validating against `celine.shacl.ttl`
   without it silently skips every `sh:SPARQLTarget` shape — the new
   `celine:DefinedTermLabelShape` and all the pre-existing `*ConceptShape`s. They do not error;
   they find no focus nodes and pass. `celine.mapper.graph.CelineGraphBuilder` sets it as of
   this release.
4. **Two mapping specs are superseded.** `obs_meter_energy` and `obs_rec_energy` map a wide row
   onto a single node, parking the second and third quantities on `peco:has_quantity` and
   `rdf:value`, which are not "the second result". Both are annotated SUPERSEDED and remain
   loadable; new work should bind `obs_energy_measurement` instead.
5. **The forecast specs are not covered.** `obs_meter_forecast`, `obs_pv_forecast` and
   `obs_rec_forecast` still point `sosa:observedProperty` at `https://w3id.org/celine/property/*`
   IRIs, which are in neither this namespace (note `celine-eu`, not `celine`) nor any other.
   v0.10 does not mint forecast properties; that is deferred.

## Migration from v0.8

1. **No term changes** — nothing is added, removed or retyped. Existing v0.8 instance data
   validates unchanged against the v0.9 profile.
2. **CIM CURIEs expand differently.** Any consumer that resolved `cim:` through the CELINE
   JSON-LD context, or copied the prefix declaration out of `celine.ttl`, now gets
   `http://iec.ch/TC57/CIM100#…` instead of `https://ontology.tno.nl/IEC_CIM/…`. Code that
   matched the old fully-expanded IRIs must be updated; code that carries the CURIE through
   unexpanded is unaffected.
3. **`cim:Company` is gone** — `celine:GridOperator` now closeMatches `cim:Organisation`.

## Migration from v0.7

1. **No term changes** — nothing is added, removed or retyped. Existing v0.7 instance data
   validates unchanged against the v0.8 profile.
2. **The ontology now conforms to its own shapes.** If you validate instance data with the
   vocabulary merged into the data graph (the recommended setup — `sh:targetNode` shapes
   fire whether or not the target appears in your data), v0.7 reported 13 scheme violations
   regardless of your data. v0.8 reports none.
3. **Language tags** — `celine:Automated`, `celine:FlexDown`, `celine:AdminCost`,
   `celine:DurationConstraint` and their siblings now carry `@en` on prefLabel and comment,
   and their schemes on label/prefLabel/description. Code matching these literals as plain
   untagged strings must match `"…"@en` instead.

## Migration from v0.6

1. **Additive only** — no v0.6 classes or properties are removed or retyped.
2. New `celine:hasDataset` property is optional — existing data validates without it.
3. `DatasetReference` gains recommended self-description slots (`dct:conformsTo`,
   `dct:format`, `dcat:accessURL`) — existing instances without them remain valid.
4. Comment-text changes are cosmetic; no domain/range/class changes to existing terms.

## Migration from v0.5

1. **Additive only** — no v0.5 classes or properties are removed or retyped.
2. `peco:Electric_POD` gains `celine:ConnectionPoint` as a new superclass — strengthens but
   does not break existing data.
3. Existing instance data continues to validate against v0.5 SHACL shapes.
4. To use new classes: type grid topology as CIM-aligned CELINE classes; assert asset-type
   instances on members via `peco:owns`.
5. Use `celine:hasLocalIdentifier` on connection points and assets as the lookup key into an
   external catalogue.

## Imports

- PECO (`https://purl.org/peco/peco-core`)
- SAREF core v3.1.1 + SAREF4ENER v1.2.1 (ETSI, versioned)
- SOSA (W3C `w3c/sdw@dee1bdd3c3`)
