# ADR-0142: Bound shape parser JSON before object construction

Status: Accepted  
Date: 2026-11-14

## Context

Worker-controlled pickle executes before parent validation. JSON removes that
execution mechanism but needs bounded allocation and a strict primitive schema.

## Decision

Keep the existing configurable 256 MiB default byte cap, feature limit, and vertex
limit. Add a maximum JSON container depth of 16 and 2,000,000 JSON values, checked
lexically before decoding. Count each container and scalar value (object keys
are not values). Reject rather than truncate. Empty arrays/objects count as one.

## Decision Provenance

Decision Venue: Codex execution conversation, 2026-11-14 UTC.  
Participants Present: operator, Codex, independent contract reviewers.  
Decision Owner: Codex for bounded implementation choices under the operator's
approved independent-remediation scope; independent security and correctness
contract reviews approved 2026-11-14.  
Implementer: Codex.

## Change Summary

Previously only file bytes were capped before unrestricted pickle allocation.
Now bytes, depth, and value count bound JSON allocation before schema validation.
No ZIP compression ratio or scientific parameter is changed.

## Rationale

Supported shapefile geometry nesting needs fewer than 16 containers. A separate
value cap constrains tiny-number/null arrays that expand disproportionately in
Python memory; two million accommodates multiple maximum-vertex 2D features
without relying solely on the 256 MiB file cap. This is a conservative security
budget, not a measured maximum-workload throughput guarantee.

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
a revised budget against container memory before raising it. Do not restore
pickle or silently bypass validation. This decision provides no sandbox claim.

## Implementation Notes

Use a string-aware lexical scan before the standard JSON decoder. JSON grammar
validation remains the decoder's responsibility. No production dependency is added.
