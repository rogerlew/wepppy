# SUDI-03 correctness and user-experience review

## Findings and verdict

No implementation findings. Correctness/QA gate: **pass**. Unresolved high,
medium and low findings: zero. Package closeout remains conditional on the owner
recording the in-progress broad regression and 7777 archive/restore evidence;
this review does not claim those checks passed. Deployment is separate.

Reviewer: independent correctness agent, 2026-09-28. Scope: working-tree changes
from contract checkpoint `e3a12ba42`, new fixtures, focused tests and live
acceptance harness/results. Checkpoint is an ancestor of HEAD and precedes
runtime changes. Authority: `docs/schemas/single-user-defined-inputs-contract.md`,
“Upload interface and validation,” plus ADR-0075 SUDI-03. Related independent
security review is a separate required gate.

## User outcome and state/error review

Opted-in users can upload a one-OFE 7777 soil through the existing independent
soil mode. Existing filename display, source download and error feedback remain;
the help now names 7777. Invalid files still produce bounded `invalid_single_input`
guidance and preserve any previously accepted source. No auth, queue, optional
source state, configuration or default serializer contract changes.

| State | Behavior and evidence |
| --- | --- |
| Absent source / fresh upload | Real `accept_source` publication test includes 7777 |
| Empty chooser / existing source | Existing unchanged source-reuse boundary; 7777 readback validates persisted version and bytes |
| Populated / replacement rejected | 7777 publication test appends hostile trailing record and verifies durable metadata and raw bytes remain unchanged |
| Supported older formats | Focused matrix retains 2006, 2006.2, 7778 and 9002; ordinary serialization unchanged |
| Malformed source | 7777 shape, labels, numeric syntax, hydraulics and 10/11-layer boundaries exercised directly |
| Working / failed / completed | Live real RQ build completes; existing source-retention and job diagnostics remain unchanged |
| Archived / restored | Owner's 7777 live check pending at review time; no archive implementation changes |

Empty source without accepted metadata, source corruption, oversize input and
active conflicts retain their established explicit error contracts. The additive
validator branch introduces no new unclassified exception or fallback behavior.

## Generated artifact evidence chain

| Stage | Evidence | Result |
| --- | --- | --- |
| Request | Authenticated multipart upload of supplied `boulderck_mica_1_7777.sol` through real rq-engine TestClient | 200 |
| Persisted source | Reloaded NoDb source version and exact raw CRLF bytes/hash | pass |
| Intermediate and prepared inputs | Native artifact tests compare every repeated OFE dictionary; independent explicit ten-field supplied fixture assertions prevent serializer/parser agreement from hiding missing fields | pass |
| Controller wiring | Live normal `_prep_multi_ofe` and `_prep_soils` service entry points | pass |
| Native execution | Supplied and synthetic fixtures at 1/2/12/32 OFEs; modifier cases at 1/3 OFEs | pass, focused log 205 passed |
| Native live output | Real run 2/12 OFEs; nonempty output without NaN/Inf markers; retained consumed inputs | pass |
| User-facing source | Authorized raw-source download byte equality | 200, pass |

Live evidence is `20260928_live_acceptance.json`, run
`/wc1/runs/si/single-input-acceptance-20260925`, with recorded service identity,
umask, source/prepared hashes and `wepp_260803`. Synthetic topology is disclosed.
A fresh RQ worker retried this run after existing workers retained old imports;
this proves local current-code acceptance, not deployment of long-lived services.

## Implementation and QA assessment

The validator admits precisely eight header fields, ten layer fields and three
restrictive fields for 7777. Header avke remains exclusive to 2006 variants;
per-layer anisotropy remains exclusive to later formats. Shared finite-number,
native depth-order, field-bound and source publication protections still apply.

The preserving writer selects the explicit 7777 field order and existing
profile-anisotropy restrictive key. Existing WSU parsing already matches native
`input.for`; no migration, hydraulic prediction or default parser behavior was
added. Compatible saturation, kslast and depth modifiers operate on generated
copies; tests retain source bytes and distinguish profile from layer anisotropy.
Authored 2400 mm depth reaches generated input unchanged; native internal depth
handling remains the acknowledged contract.

Changes are small and localized. Tests extend established parameter matrices,
exercise owned consumers directly and include both nondefault synthetic values
and the operator's exact CRLF fixture. Existing mocks cover surrounding topology,
not the changed parser/serializer or native execution boundary. Real controller
and transport evidence complements those tests. No speculative abstractions,
dependencies, parameter defaults or hidden artifact paths were introduced.

Inputs, intermediates, failure diagnostics and outputs retain established project
browse/download/archive paths. No observability exception is requested. Highest
supported claim at review time: implemented and locally executed with consumed
artifact verification; global regression/archive completion and deployment remain
separately identified above.

## Owner archive follow-up

The actual archive/restore completed successfully after review; retained source
metadata and bytes/hash match. See `20260928_archive_acceptance.json`. The broad
regression result remains pending. No further production edits followed review.

## Owner final gate completion

Full regression completed: 9892 passed, 99 skipped, 12 subtests passed, exit 0.
Archive/restore, frontend, stub completeness, exception and docs gates passed.
All closeout conditions are satisfied; no production changes followed review.
