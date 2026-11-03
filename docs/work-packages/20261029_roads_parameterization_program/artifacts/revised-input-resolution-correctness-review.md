# Roads input resolution correctness review

## Metadata and scope

Reviewer: independent `resolver_review` agent, 2026-11-03. Starting implementation
revision: `e0308765c6da2e8ec73c88208abcb0d98bd684e8`. Scope is
`Roads._resolve_segment_run_inputs`, the active optional buffer-profile helper,
its direct segment-detail and execution
consumers, focused regression coverage, and generated slope/soil propagation.
This review does not approve configuration UI or persistence/application changes.

Canonical authority: Roads `specification.md`, “Run-Level Parameter Defaults”,
“Fill parameter contract”, and “Step-3 as-implemented contract notes”; the latter
requires explicit fill defaults when attributes are missing/invalid. The Roads
adjudication contract requires finite/valid inputs and outputs, actual generated
artifact evidence, and disposition of confirmed defects. Contract-first
“Conformance Fixes and Urgent Restoration” permits restoring unchanged intent.

## Preimplementation classification

The correction is **conformance**, provided its boundary remains the local resolver:
nonfinite numeric attributes use the same existing configured fallback as
unparsable attributes, and provenance reports the source that actually supplied
the effective value. NaN and infinity are invalid measurements; min/max converting
NaN into 100% fragments, 150% fill slope or 100 m fill length cannot establish a
valid operator selection. No new default, threshold, finite-range policy or
scientific transfer function is authorized by this correction.

Preserve all finite clipping rules, valid attribute precedence, aliases, and the
separate required-field validation for unrutted profiles. Do not globally change
`_coerce_float`: unrelated consumers have not been adjudicated here. A new override
mode or changed finite fallback rule would be new intent and needs its own gate.

## User outcome and failure-class coverage

Users must receive prepared geometry/material inputs from valid feature values or
existing configured defaults, with truthful provenance. Invalid optional attributes
must not silently become maximum physical values. No new user-facing exception is
required for these already-defaulting fields.

| Consumer | Consequence | Required regression |
| --- | --- | --- |
| Segment detail resolver/readback | Incorrect default/source explanation | Direct resolver source labels for absent, invalid, valid and aliased attributes |
| Inslope and rutted execution resolver | Invalid road width/RFG provenance; nonfinite RFG maximum | Finite resolved values and canonical soil/slope readback |
| Rutted fill geometry and default-use counter | Nonfinite fill becomes maximum; missing fallback count | Nonfinite fill fallback, source label and generated fill geometry |
| Channel-associated rutted buffer helper | Nonfinite buffer values become maxima | Existing derived fallback and source labels; finite clipping unchanged |
| Unrutted replacement resolver | Shared optional fields change consistently | Required fill/buffer rejection still enforced by separate validator |

This is not a class-wide assertion about every use of `_coerce_float` in Roads.
The unchanged unrutted required-profile parser separately checks finite values.

## Valid-state and error policy

| State | Expected behavior | Evidence status |
| --- | --- | --- |
| Roads absent/never used | Existing module activation and lifecycle unchanged | No boundary change |
| Empty feature properties | Existing defaults and roads_default provenance | Covered by direct resolver/writer tests below |
| Populated valid attributes | Preserve values, finite clipping and segment_property provenance | Covered by direct resolver/writer tests below |
| Supported legacy aliases | Same resolution and source semantics | Covered by direct resolver/writer tests below |
| Invalid optional attributes | Existing configured fallback; no new exception | Covered by direct resolver/writer tests below |
| Invalid required unrutted geometry | Existing explicit segment failure | Covered by direct resolver/writer tests below |

Hostile filesystem paths, authorization, serialization and locking are outside
this local parsing patch; their boundaries must not be edited. Security impact is
limited to handling invalid numeric values, with no new execution surface.

## Generated artifact evidence

Review acceptance requires direct unmocked resolver calls and canonical slope/soil
writers followed by semantic readback, not merely assertion of an intermediate
number. The separate disposable-project sensitivity lane may establish current
controller propagation for valid values. It cannot substitute for the malformed
attribute regressions. Existing source/project/baseline preservation obligations
remain unchanged. No historical artifact is migrated or certified.

## Implementation review and retained checks

The implementation adds finite guards only in the four optional numeric resolver
branches and two optional buffer branches. Texture/RFG/width labels now track
actual accepted source. `_coerce_float`, normalization aliases, numeric constants,
finite clipping, required-unrutted parser, persistence and execution paths are
unchanged. No broad exception handler or dependency was introduced.

Independent command:

    wctl run-pytest tests/nodb/mods/test_roads_controller.py -k 'segment_invalid_numeric or segment_finite_aliases or unrutted_required_geometry or supports_outslope_rutted_fill_defaults' -q

Result: **9 passed, 50 deselected**, 2 dependency deprecation warnings, 9.76 s.
The direct failing boundary is the real resolver and optional-buffer helper;
neither is mocked. The parameterized invalid cases cover malformed text, NaN,
positive and negative infinity with nonstandard configured defaults. Real canonical
writers produce and reparse slope lengths/grades/width and soil horizon RFG values.
These prove malformed input propagation is corrected, including the distinct
road/fill/buffer RFG transforms (65%, 38.5%, 12% for the selected 12% request).

Existing fill-default/override coverage passes in that command. New alias/zero/
finite clipping assertions preserve texture aliases, RFG zero and caps, width
fallback and source, and finite fill clipping. Required unrutted nonfinite fields
still return explicit invalid-field results. A separate added finite-buffer test
covers legacy aliases, ordinary values, both caps and segment_property provenance;
the complete controller suite passed it. The retained
[before log](revised-input-resolution-before.log) records 5 failures and 3 passes;
the [after log](revised-input-resolution-after.log) records **59 passed**, including
the finite-buffer control. I independently read both logs. Reviewed production
source SHA256: `7506718831d8a8b11ca0877cd75aa82596d0aeb900cf04505f29df864bd77a4d`.
The specification and ENDUSER notes accurately describe unchanged invalid-value
fallback intent, preserve required unrutted rejection and do not certify old outputs.

No storage, locking, archive path or permission boundary changed. Browser/native
full-workflow and broader repository gates remain the parent execution's separate
obligations; this review does not claim them from focused tests.

## Findings and verdict

Preimplementation scope classification: **pass for bounded conformance repair**.
Implementation verdict: **pass for reviewed local patch and direct generated-input
regression evidence**. Unresolved findings in the local patch: none. Broader
repository validation and the eventual approved browser workflow remain separate
gates.
No deployment or whole-program completion recommendation is made. New artifact
paths, retention policy, archive exclusions or browser routes are not proposed;
existing visible Roads outputs and history remain the observability authority.
