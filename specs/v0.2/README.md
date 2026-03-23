# CELINE Core Semantic Stack

This repository contains the **core semantic definition** of CELINE, starting from a single authoritative ontology (`celine.ttl`) and deriving the corresponding **validation** and **serialization** artifacts:

- SHACL shapes
- JSON-LD context/representation
- JSON Schema for API-level validation

The intent is to maintain **one source of truth** for meaning, and generate or align all other artifacts from it.

---

## 1. [celine.ttl](celine.ttl) - Core Ontology (Authoritative)

**Format:** RDF / Turtle  
**Role:** Semantic source of truth

`celine.ttl` defines the **conceptual model** used across CELINE services.  
It declares:

### Core Classes
- `celine:EnergyCommunity`
- `celine:Participant`
- `celine:Membership`
- `celine:Site`
- `celine:Asset`
- `celine:Meter`
- `celine:TimeSeries`

### Core Relationships & Properties
- Identity and linkage:
  - `celine:authURI`
  - `celine:datasetURI`
  - `celine:sensorId`
- Structural relations:
  - `celine:hasMembership`
  - `celine:isOwnedBy`
  - `celine:locatedAt`
  - `celine:connectedTo`
  - `celine:observedEntity`

### Purpose
- Provide **stable semantics** independent of any specific API or storage model
- Enable reasoning, linking, and interoperability
- Act as the reference for all downstream validation rules

All other artifacts must be **consistent with this ontology**.

---

## 2. [celine.shacl.ttl](celine.shacl.ttl) - SHACL Validation Profile

**Format:** SHACL (RDF)  
**Depends on:** `celine.ttl`

The SHACL file defines **constraints** on RDF graphs that use the CELINE ontology.

### What SHACL Validates
Examples of enforced rules:
- A `celine:Participant` **must** have exactly one `celine:authURI`
- A `celine:Meter` **must**:
  - have a `celine:sensorId`
  - be owned by a `celine:Participant`
- A `celine:TimeSeries` **must**:
  - reference a `celine:datasetURI`
  - reference exactly one observed entity
- A `celine:Membership` role must be one of:
  - `operator`
  - `prosumer`
  - `consumer`

### Scope
- SHACL validates **graph-level semantics**
- It runs **after** data has been converted to RDF/JSON-LD
- It does not validate JSON/YAML syntax

SHACL ensures semantic correctness, not just structural correctness.

---

## 3. [celine.jsonld](celine.jsonld) - JSON-LD Representation

**Format:** JSON-LD  
**Derived from:** `celine.ttl`

This file provides a **JSON-compatible representation** of the CELINE ontology.

### Role
- Bridge between RDF and JSON-based systems
- Enable conversion pipelines:
  - YAML / JSON → JSON-LD → RDF
- Preserve:
  - global identifiers (IRIs)
  - class semantics
  - relationships

### Intended Usage
- Internal processing
- Interoperability with RDF tooling
- Not intended for manual authoring

JSON-LD ensures that JSON data remains semantically equivalent to RDF.

---

## 4. [celine.schema.json](celine.schema.json) - JSON Schema

**Format:** JSON Schema (Draft 2020-12)  
**Aligned with:** `celine.ttl`

This schema validates **REC registry documents** at the API or configuration level.

### What JSON Schema Validates
- Required fields are present
- Field types are correct
- Structural consistency of registry documents
- Identifier fields accept:
  - full IRIs, or
  - CURIEs (e.g. `auth:users/123`)

### What JSON Schema Does NOT Validate
- Semantic constraints across entities
- Ontology-level consistency
- Role inference or reasoning

Those concerns are handled by **SHACL**.

---

## 5. Relationship Between Artifacts

```text
celine.ttl
   ↓ (defines meaning)
celine.jsonld
   ↓ (serialization)
RDF graph
   ↓ (validation)
celine.shacl.ttl

REC JSON / YAML
   ↓ (structural validation)
celine.rec.schema.json
```

- `celine.ttl` defines **what things mean**
- `celine.shacl.ttl` defines **what is allowed**
- `celine.jsonld` defines **how RDF is exchanged as JSON**
- `celine.rec.schema.json` defines **what APIs accept**

---

## 6. Design Rationale

- Avoid duplicating semantics across formats
- Keep validation layered and explicit
- Allow gradual tightening of constraints
- Remain compatible with semantic web standards and data spaces

This approach ensures CELINE remains:

- interoperable
- auditable
- evolvable
