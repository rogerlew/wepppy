# MIPA-01 independent contract correctness review

## Metadata and scope

Reviewer: `mipa_contract_correctness` (independent reviewer agent), 2026-11-02.
Starting WEPPpy revision: `3c4b6fe839a4caea62b5f92bb16ba482de7ab703`.
Reviewed the proposed `docs/schemas/mofe-input-identity-contract.md`, its links
from the management/Disturbed mapping contracts, and
`artifacts/20261102_contract_decision.md`. Inspected management parsing,
serialization, rotation/MOFE synthesis, generic PMET writing, normal preparation,
and the native `scenhd.for`, `pmetcoef.for` and `contin.for` interfaces.
This is read-only design review, not implementation or native validation.

## Findings

### MIPA-COR-01 — Medium: common-period expansion needs a bound before allocation

`docs/schemas/mofe-input-identity-contract.md:29–50` requires materializing the
least common multiple of complete source calendars and checks limits only
before publication. Two individually admitted periods of 991 and 997 years
produce a 988,027-year intermediate even when the requested simulation is short;
additional relatively prime periods can multiply this sharply. Small source
scenario counts do not bound timeline-object count.

The unchanged upload contract at
`docs/schemas/single-user-defined-inputs-contract.md:109–118` requires bounds
before count-driven allocation and source years in 1–1000. The proposed
checkpoint must not permit large allocation before discovering an output limit.

Required disposition: distinguish the mathematical common period from its
materialized timeline. Calculate/bound counts before allocation using applicable
existing limits, or produce only the requested duration without losing source
phase. If the current synthesis interface cannot preserve a valid requested
duration without an enormous intermediate, resolve that interface choice before
implementation rather than inventing a scientific minimum/maximum. Retain a
regression for relatively prime periods with a short requested duration, as well
as the planned 1/2- and 2/3-year tests.

### MIPA-COR-02 — Medium: alias rewriting lacks a repeat-call contract

`docs/schemas/mofe-input-identity-contract.md:65–69` permits rewriting staged
management names while keeping coefficient mappings keyed by pre-alias names.
`wepppy/wepp/management/pmetpara.py:22–31` discovers mapping keys by reparsing the
same files on each call. `managements.py:2428–2429` discards comments, including
the proposed comment-only provenance. After a first successful alias rewrite,
the same public call with the same original mappings can therefore discover
aliases and fail, or a repair may generate a second alias generation. The
normal preparation retry clause does not settle direct repeated use of the
preserved `pmetpara_prep(runs_dir, kcb, rawp)` API.

Required disposition: specify where alias ownership/provenance lives and how a
repeat writer invocation recovers source identity without hand editing or
coefficient-key changes. Require idempotent names, references and coefficients
for two identical direct calls, changed coefficients on a subsequent call,
and retry after interruption between management rewriting and PMET publication.
Preserve useful partial evidence and existing failure status; this does not
require introducing a new transaction service or datastore.

### MIPA-COR-03 — Medium: eight-character ASCII is insufficient native token safety

`docs/schemas/mofe-input-identity-contract.md:62–69` constrains aliases to ASCII
and eight characters, but ASCII includes spaces, commas, quotes and slash.
Native `scenhd.for:25–26,47` reads a fixed-width A8 name, whereas
`pmetcoef.for:58–63,70–72` uses list-directed token reads. A raw `Crop A` name
can be a valid A8 management key but becomes a different first token in the
unquoted CSV emitted at `pmetpara.py:41`; collisions are not necessary for this
failure. Merely preserving a unique short name can still invoke fallback or
misparse coefficients.

Required disposition: define native key equivalence using the actual A8 and
list-directed readers, including padding/truncation and case behavior. Require
token-safe emitted aliases (for example an explicitly restricted alphabet) or
correct native quoting, and apply the policy to unsafe retained names even
without a collision. Add distinct native reader tests for a short whitespace
name, separator/control cases, long common prefixes and ordinary safe names.
Do not change upload admission merely to avoid a generated-copy encoding issue.

## User outcome, states and error policy

The proposed outcome is faithful per-OFE calendars, soil/cover ordering and PMET
coefficients. Absent optional state, empty collector directory, populated state,
legacy inputs, immutable uploads, malformed geometry, failed preparation and
archive/restore are explicitly covered. Zero enabled-buffer rejection and
nonrepresentable segment rejection have a stated rationale; positive overlong
buffers and ignored `min_length` retain their current behavior.

The design correctly separates producer success from NATIVE-01/02/03 acceptance.
Native capacities, wrong-owner FC/HK behavior and the scientific HOLD are not
waived. Generic/Disturbed and ordinary/deduplicated variants are named, including
residue references and all crop scenarios rather than only currently active crops.

## Generated artifact and observability assessment

The baseline evidence reproduces failures; it is not repair acceptance. The
proposal requires generated/prepared file hashes and semantic readback, exact
module/binary provenance, an actual-project clone, fresh native outputs/reports,
failure/retry and normal browse/download/archive/restore coverage. No hidden
artifact directory or exception to immutable-source preservation is introduced.
Actual-project, 9005 consumer and full worker-boundary evidence remain pending.
This review did not run native models, edit production sources or rerun tests.

## Verdict

Design-readiness gate: **fail pending disposition of three medium findings**.
High findings: 0. Medium findings: 3. Low findings: 0.

Operator ratification, standalone ancestor commit and native repair authority
remain distinct gates. Resolving this review does not confer any of those
authorities or constitute implementation correctness/security approval.
After contract corrections, request focused readback of the three dispositions.

## Disposition readback — 2026-11-02

Reviewed the revised canonical contract at SHA256
`96be019120c70ca0abc15127330b86056b7cec26e3f875f0f9d0bf16d5258eab`
and checkpoint at SHA256
`1305fe59019289720c1ff090233a42f4d8503693b18e1c82a4e2957e2ccadafb`.

- **MIPA-COR-01 resolved at contract boundary:** the common period is logical;
  known N expands directly, existing applicable limits are checked before
  count-driven allocation, and a large common period cannot itself reject a
  supported short simulation. Coprime-period regression is explicit. A future
  implementation must still show how normal preparation supplies N to synthesis.
- **MIPA-COR-02 resolved at contract boundary:** validated machine-readable
  original-name/context comments must survive reparsing; direct repeats,
  changed mapping values and archive/restore preserve source-key semantics and
  stable references. Missing/contradictory alias provenance has an explicit
  rebuild policy. This requires dedicated implementation tests; comments alone
  without a reader are not compliance.
- **MIPA-COR-03 resolved at contract boundary:** aliases use a letter-led
  letters/digits/underscore alphabet of at most eight characters; unsafe retained
  identities must round-trip through both native readers or be aliased. Exact
  native-key uniqueness remains required. The checkpoint adds token and retry
  regressions rather than claiming native validation already passed.

The existing exclusion is now correctly identified as filenames containing
`pw0`, without creating a new channel filter. The prior findings are retained
above as review history, not current unresolved defects.

Final design-readiness verdict: **pass**. Unresolved design findings: High 0,
Medium 0, Low 0. This approves the proposed contract for operator review only;
ratification/ancestor-commit gates, dedicated implementation security review,
producer/native acceptance and deployment remain outstanding. No production
correctness or release approval is implied. Review artifact doc-lint passed
with zero errors and warnings before this disposition; final package lint should
include the appended disposition.
