# ADR-0142: Bound shape parser JSON before object construction

Status: Accepted  
Date: 2026-11-14

## Context

Worker-controlled pickle executes before parent validation. JSON removes that
execution mechanism but needs bounded allocation and a strict primitive schema.

## Decision

Use a configurable 16 MiB parser JSON cap, 128 MiB uncompressed/parser-input
cap, 320 MiB request-scratch cap, 384 MiB parser address-space limit, and 32 MiB
serialized-output cap inside a 1.5 GiB container. Admit one inspect or conversion
request at a time globally and per client; this single-flight limit is part of
the memory invariant. Retain the feature and vertex limits. Apply a maximum JSON
container depth of 16 and 2,000,000 JSON values,
checked lexically before decoding. Count each container and scalar value (object
keys are not values). Reject rather than truncate. Empty arrays/objects count as
one.

## Decision Provenance

Decision Venue: Codex execution conversation, 2026-11-14 UTC.  
Participants Present: operator, Codex, independent contract reviewers.  
Decision Owner: operator for fail-closed service availability and Codex for the
bounded remediation values under the approved execution scope. Independent
security review required an aggregate invariant on 2026-11-14.
Implementer: Codex.

## Change Summary

The initial Rust candidate allowed 256 MiB parser JSON, 600 MiB uncompressed
input, 700 MiB scratch, 512 MiB parser address space, and 100 MiB output inside a
1 GiB container. The amended envelope uses the limits above and fails closed.
No ZIP compression ratio or scientific parameter is changed.

## Rationale

Supported shapefile geometry nesting needs fewer than 16 containers. The
independent review showed the initial independently configured maxima could
exceed the cgroup when tmpfs charging, parser RSS, retained archive bytes, JSON
bytes/text/objects, Shapely objects, and serialized output overlapped. The lower
limits, larger cgroup, and single-flight admission prevent independently bounded
requests from multiplying parser address-space and scratch ceilings. They create
a conservative envelope for exact-image near-ceiling validation, not a
maximum-workload throughput guarantee.

## Alternatives Considered

Byte-only JSON still permits deep nesting and disproportionate allocation.
Object validation only after decoding is too late to bound decoder allocation.
A streaming dependency adds unnecessary deployment and maintenance costs.

## Consequences

Very large valid datasets may now fail explicitly before the preexisting feature
or byte limit. The total-value limit includes coordinate numbers and properties;
tests must establish exact edges and ordinary point/line/polygon/multipart/null
parity. This compatibility limit must be stated in operator documentation.

## Evidence

- [Contract](../../wepppy/microservices/shape_converter/docs/specification.md#independent-remediation-contract-2026-11-14).
- [Baseline](../work-packages/20261113_shape_converter_security_conformance/artifacts/20261114_m0_baseline_and_sandbox_probe.md).
- Focused red/green and semantic evidence will be recorded in the active package.

## Risk and Rollback Notes

If valid workloads exceed this budget, retain bounded fixture evidence and review
a revised budget against container memory before raising it. If the service
cannot meet the budget, deployment must leave shape-converter stopped. Do not
restore pickle, GDAL/Fiona, or silently bypass validation. This decision provides
no sandbox claim.

## Implementation Notes

Use a string-aware lexical scan before the standard JSON decoder. JSON grammar
validation remains the decoder's responsibility. No production dependency is added.
