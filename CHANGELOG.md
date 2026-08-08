# CHANGELOG

<!-- version list -->

## v1.4.0 (2026-08-08)

### Chores

- Add AGENTS.md
  ([`95e03b6`](https://github.com/celine-eu/ontologies/commit/95e03b6fb5cc9b1116eedb9e4ff4749734264997))

- Add flexibility request, add REC members mapping
  ([`c2db39e`](https://github.com/celine-eu/ontologies/commit/c2db39e62f2fe95ad7256b99417ef38eb76fe8e1))

- Add member roles and status
  ([`50d4098`](https://github.com/celine-eu/ontologies/commit/50d40986077266938b5fb4d018ee5021f31afa52))

- Add release
  ([`5e7f151`](https://github.com/celine-eu/ontologies/commit/5e7f1512461b5f8d82669aeeda6c038a13ce3545))

- Add sharing group for administrative groups in each REC
  ([`9445ce5`](https://github.com/celine-eu/ontologies/commit/9445ce5f70e820e01c6aca69128f4bc77907df12))

- Add widoco serve
  ([`25d3928`](https://github.com/celine-eu/ontologies/commit/25d39287956ba044c5b05b70761337cdc75b7cf4))

### Features

- Add rec registry details to ontology
  ([`7615fc0`](https://github.com/celine-eu/ontologies/commit/7615fc05c6ab8547b8dce33c0a7c116af2280935))

- Add v0.7 generalize dataset references using dcat tags
  ([`efd5679`](https://github.com/celine-eu/ontologies/commit/efd56793f88bfac9b7e06598e604fe8ee351d6ef))

- Fix shacl bug, add concept to types
  ([`658067b`](https://github.com/celine-eu/ontologies/commit/658067bb3b108f38b378200c0491f889810f66b4))


## Ontology v0.8 (2026-08-08)

Conformance fix. No new terms; nothing removed or retyped.

### Fixed

- **SKOS top concepts**: `CommitmentMode`, `FlexibilityDirection`, `CostType` and
  `ConstraintType` now declare `skos:hasTopConcept`. These four schemes were carried
  forward from v0.4 without it, so v0.7 failed its own `*SchemeShape` constraints
  (`skos:hasTopConcept` minCount 1) — 13 violations reported against any data graph,
  since the shapes use `sh:targetNode`. The concepts already declared `skos:inScheme`
  and `skos:topConceptOf`; only the scheme-side assertion was missing. All four schemes
  are flat (no `skos:broader` in the ontology), so every member is a top concept. The
  shapes are unchanged.
- **Language tags**: labels, prefLabels, descriptions and comments in those four scheme
  blocks gain `@en`, matching the nine schemes from v0.5+. Consumers matching these
  literals as plain untagged strings must match the tagged form.

### Deferred

- SHACL shapes for v0.6 grid topology and asset classes.

## Ontology v0.7 (2026-05-27)

### Features

- **hasDataset property**: new object property `celine:hasDataset` — (ConnectionPoint ∪
  peco:Asset) → DatasetReference. Links an asset or connection point to an external,
  self-describing datasource. Operational counterpart to the SimulationRun-scoped
  `usesDataset`/`producesDataset`.
- **DatasetReference self-description**: updated comment and example to note that instances
  SHOULD declare conformance target (`dct:conformsTo`), format (`dct:format`), and access
  location (`dcat:accessURL` or `dct:source`) via DCAT/Dublin Core terms.
- **DCAT prefix**: added `dcat:` prefix declaration (no `owl:imports`).
- **Implementation-neutral wording**: replaced all "rec-registry catalogue" references with
  neutral "external catalogue" phrasing across ontology header, asset class comments
  (`PVSystem`, `BatteryStorage`, `EVCharger`, `HeatPump`), member property comments
  (`hasMemberRole`, `hasMemberStatus`, `hasDeliveryPoint`), and `hasLocalIdentifier`.

### Deferred

- SHACL shapes for v0.6 grid topology and asset classes.

## Ontology v0.6 (2026-05-14)

### Features

- **Grid topology**: 6 new classes — `Substation` (abstract), `PrimarySubstation` (HV/MV),
  `SecondarySubstation` (MV/LV), `PowerTransformer`, `DistributionFeeder`, `RegulatoryZone`
  (administrative coverage area). All grid equipment classes are `rdfs:subClassOf peco:Asset`;
  CIM alignment via `skos:closeMatch` to IEC 61968 profile (no `owl:imports`).
- **Grid actor**: `GridOperator` class (`rdfs:subClassOf peco:Agent`, `skos:closeMatch
  cim:Company`). DSO specialisation noted in comment; role-based modelling deferred.
- **Connection point**: `ConnectionPoint` class with `skos:closeMatch cim:UsagePoint`.
  `peco:Electric_POD` declared `rdfs:subClassOf celine:ConnectionPoint` — the single
  statement where v0.6 reaches into PECO's namespace.
- **Asset inventory (presence-only)**: 5 new classes — `PVSystem`, `BatteryStorage`
  (via `peco:Energy_storage`), `ElectricityMeter`, `EVCharger`, `HeatPump`. SAREF
  alignment via `skos:closeMatch` only. No technical-attribute datatype properties;
  specs live in the external rec-registry catalogue.
- **9 new object properties**: `hasIdentifierScheme`, `operatedBy`, `servedBy`,
  `inRegulatoryZone`, `hasRegulatoryZone`, `hasTopologyNode`, `hasGridOperator`,
  `pairedWith` (symmetric), `measures`.
- **1 new datatype property**: `hasLocalIdentifier` — unified local-ID property for
  connection points (POD/CUPS/PRM/etc.) and assets (registry lookup key).
- **SKOS scheme**: `ConnectionPointIdentifierScheme` with 6 concepts — `POD` (Italy),
  `CUPS` (Spain), `PRM` (France), `MALO` (Germany), `EAN` (Belgium/Netherlands),
  `MPAN` (United Kingdom).
- **CommunityContext extended**: gains `hasRegulatoryZone`, `hasTopologyNode`,
  `hasGridOperator` optional properties.
- **Member classification**: `MemberRole` SKOS scheme (Consumer, Prosumer, Producer,
  Operator, Admin) and `MemberStatus` SKOS scheme (Pending, Active, Suspended, Inactive)
  with `hasMemberRole` and `hasMemberStatus` properties on `peco:Energy_community_member`.
- **Flexibility request**: `FlexibilityRequest` class — demand signal from operator/system
  requesting members to activate flexibility. Linked to `FlexibilityCommitment` via
  `resultsInCommitment` / `inResponseTo` (inverse pair). `RequestStatus` SKOS scheme
  (Open, Fulfilled, Partially Fulfilled, Expired, Cancelled). `hasFlexibilityDirection`
  domain widened to cover both commitments and requests.

### Deferred

- Asset technical attributes, asset-type sub-classification
  schemes, generic `Load` class, device metadata, telemetry layer, closed-world absence,
  SHACL shapes for new classes.

## v1.3.0 (2026-05-05)

### Features

- Add v0.5 with generalized KPIs definitions
  ([`fa9c3cf`](https://github.com/celine-eu/ontologies/commit/fa9c3cffabe591fdb0acd81056944aeb608f9437))


## Ontology v0.5 (2026-05-05)

### Features

- **KPI container**: new `KPIDefinition` class with scope, calculation method, temporal
  granularity, and unit of measure properties
- **KPI catalog**: `KPICatalog` SKOS concept scheme with 11 initial REC-relevant KPI entries
  (SelfConsumptionRate, SelfSufficiencyRate, SharedEnergy, SharedEnergyMemberShare,
  IncentiveAccrued, IncentiveMemberShare, WithdrawnEnergy, FedInEnergy,
  LocalGenerationEnergy, PeakReductionAchieved, FlexibilityActivated)
- **KPI evaluation refactor**: `KPIEvaluation` now links to `KPIDefinition` via
  `hasKPIDefinition` with mandatory `hasKPIValue`, `hasEvaluationTimeInterval`,
  `hasEvaluatedScope`; optional `hasInputObservation` and `hasInputKPIEvaluation` for
  derived KPIs
- **SKOS vocabularies**: four new concept schemes — `KPIScope`, `KPICalculationMethod`,
  `KPITemporalGranularity`, `UnitOfMeasure`
- **SKOS alignment**: class-level `skos:closeMatch` / `skos:relatedMatch` toward
  SAREF4CITY KeyPerformanceIndicator, BIGG4KPI KPIAssessment

### Breaking Changes

- Removed `owl:imports` for BIGG ontology and BIGG4KPI extension
- Removed `celine:evaluatesKPI` property (replaced by `celine:hasKPIDefinition`)
- Removed `bigg:` prefix from JSON-LD context and SHACL shapes
- `KPIEvaluation` now requires `hasKPIDefinition`, `hasKPIValue`,
  `hasEvaluationTimeInterval`, `hasEvaluatedScope` (previously only `evaluatesKPI` was
  required)

## v1.2.0 (2026-03-24)

### Chores

- Fix md
  ([`6bd483d`](https://github.com/celine-eu/ontologies/commit/6bd483dbecbbb27beb3ede28c06ff697ade8aeb3))

- Use celine-eu for w3id.org
  ([`a1bf0b3`](https://github.com/celine-eu/ontologies/commit/a1bf0b3cf1f82ecc5fffc3ffcd75760789bbcfd3))

### Features

- Add settlement model
  ([`872667d`](https://github.com/celine-eu/ontologies/commit/872667d52661eccbb67cc5cd9b5e91d3831d7e0c))


## v1.1.0 (2026-03-23)

### Chores

- Add widoco docs gen
  ([`3f22615`](https://github.com/celine-eu/ontologies/commit/3f226157daaa35afb3e6d365514a59823808cf19))

- Add widoco docs, review strucuture for releases
  ([`ae50d89`](https://github.com/celine-eu/ontologies/commit/ae50d8982153145cb4eb9092603991a1c30aaa53))

- **deps**: Bump rdflib from 7.5.0 to 7.6.0
  ([`f2daefe`](https://github.com/celine-eu/ontologies/commit/f2daefe6191974a576f0fde774513f8728ca12ec))

- **deps**: Bump typer from 0.21.1 to 0.24.1
  ([`bf5287c`](https://github.com/celine-eu/ontologies/commit/bf5287c7f348c86b3743afdb4c84fecdf0e277d8))

### Continuous Integration

- Bump peter-evans/repository-dispatch in the actions group
  ([`ff34b9a`](https://github.com/celine-eu/ontologies/commit/ff34b9aea5afd5324b1641ba9f7945384311fadf))

### Features

- Separate mapper and cli subpackages
  ([`fafe818`](https://github.com/celine-eu/ontologies/commit/fafe81842b1f551a12bd37bfe7522ef4018d3fe8))


## v1.0.1 (2026-03-22)

### Bug Fixes

- Restructure src
  ([`928a9c3`](https://github.com/celine-eu/ontologies/commit/928a9c3d7a41946913d4ff3bba242ab0bca42f70))


## v1.0.0 (2026-03-22)

- Initial Release
