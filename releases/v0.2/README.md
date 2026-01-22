# CELINE Core Semantic Stack

This package contains the core semantic definition of CELINE, starting from a single authoritative ontology (celine.ttl) and deriving the corresponding validation and serialization artifacts: SHACL shapes, JSON-LD, and JSON Schema.

The intent is to maintain one source of truth for meaning, and align all other artifacts to it.

---

## 1. celine.ttl — Core Ontology (Authoritative)

Format: RDF / Turtle

Role: Semantic source of truth

celine.ttl defines the conceptual model used across CELINE services. It declares the core classes and predicates that represent the domain semantics.

Core classes include:
- EnergyCommunity
- Participant
- Membership
- Site
- Asset
- Meter
- TimeSeries

Core predicates include:
- authURI (link to authentication / identity systems)
- datasetURI (link to external datasets)
- sensorId (non-PII identifier for metering)
- hasMembership
- isOwnedBy
- locatedAt
- connectedTo
- observedEntity

The ontology provides stable semantics independent of APIs, storage, or serialization formats. All other artifacts must remain consistent with this file.

---

## 2. celine.shacl.ttl — SHACL Validation Profile

Format: SHACL (RDF)

Depends on: celine.ttl

The SHACL profile defines semantic constraints on RDF graphs that use the CELINE ontology.

Examples of enforced constraints:
- A Participant must have exactly one authURI
- A Meter must have a sensorId and be owned by a Participant
- A TimeSeries must reference a datasetURI and an observed entity
- Membership roles must be one of: operator, prosumer, consumer

SHACL validates graph-level semantics and relationships. It is applied after data has been converted to RDF or JSON-LD. It does not validate JSON or YAML syntax.

---

## 3. celine.jsonld — JSON-LD Representation

Format: JSON-LD

Derived from: celine.ttl

This file provides a JSON-compatible representation of the CELINE ontology.

Its role is to bridge RDF and JSON-based systems, enabling conversion pipelines such as:
- YAML or JSON to JSON-LD
- JSON-LD to RDF

JSON-LD preserves global identifiers, class semantics, and relationships. It is intended for interoperability and internal processing, not for manual authoring.

---

## 4. celine.rec.schema.json — JSON Schema

Format: JSON Schema (Draft 2020-12)

Aligned with: celine.ttl

The JSON Schema validates REC registry documents at the API or configuration level.

It ensures:
- Required fields are present
- Field types are correct
- Structural consistency of documents
- Identifier fields accept either full IRIs or CURIEs

JSON Schema does not perform semantic reasoning or cross-entity validation. Those concerns are handled by SHACL.

---

## 5. Relationship Between Artifacts

celine.ttl defines meaning.
celine.jsonld provides a JSON serialization of that meaning.
celine.shacl.ttl validates RDF graphs built from that meaning.
celine.rec.schema.json validates JSON or YAML documents before semantic processing.

---

## 6. Design Rationale

This layered approach avoids duplicating semantics, keeps validation explicit, and aligns with semantic web and data space practices. It allows CELINE to remain interoperable, auditable, and evolvable while preserving developer usability.