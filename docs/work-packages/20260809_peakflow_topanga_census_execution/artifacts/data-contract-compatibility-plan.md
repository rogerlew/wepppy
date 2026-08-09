# Topanga Census Execution Data-Contract Compatibility and Regression Plan

## Scope and Timing

This plan was written before execution code, schemas, or generated census data
were changed. It governs the additive execution layer for the immutable Topanga
trial plan. The preparation plan remains byte-for-byte unchanged at SHA-256
`32e6f5e99a77747fcdd93388302f2a5ffb496a87b764ac4505e09691955db756`
and plan ID
`b575fde4a28cf85f1d28e0dfff305472b5419fd9b3639d39dc437600617080de`.
The accepted Phase 2A evidence and preparation artifacts remain read-only
compatibility authorities.

The execution layer is additive. It does not rename, remove, reinterpret, or
rewrite preparation fields, eligibility, mutation values, screening floors,
event keys, units, or null meanings. Unsupported schema major versions fail
explicitly. Compatible additions use optional fields or a minor version.

## Artifact Inventory and Contracts

The committed execution selection is versioned JSON containing its schema
version, selection ID, frozen plan ID, frozen plan-file SHA-256, and the ordered
1,088 unique eligible trial IDs. It contains no outcomes. Its selection ID is
the canonical content hash of all fields except the embedded ID.

The committed preflight report is versioned JSON. It records the plan and
selection bindings; requested, eligible, excluded, and selected totals; source
tree, per-input, executable, path-boundary, symlink, storage, and prior-terminal
checks; canonical roots; available and projected bytes; timestamp; and an
explicit pass or fail verdict. A failed check is never omitted or converted to
a warning.

The external progress snapshot is versioned JSON bound to the plan, plan file,
selection, terminal schema, and executable hashes. It counts selected,
complete, failed, stopped, pending, and active trials. Counts are mutually
exclusive and sum to the selected denominator. It is written atomically and is
observational; it does not authorize selection changes.

Each existing `1.0.0` terminal remains one current attempt disposition with
`complete`, `failed`, or `stopped` status and bindings for plan, trial, source
input, executable, and terminal schema. Execution adds no incompatible changes
to those meanings. A matching complete terminal is reusable only after its
declared trace and hillslope-pass paths and hashes validate. Failed or stopped
attempts are retained as `terminal.attempt-*`, `runs.attempt-*`, and
`output.attempt-*` before retry. Missing terminals remain pending.

The external terminal ledger has one row per selected trial. It preserves the
terminal status and binding fields, mutation realization, runtime in seconds,
return code nullability, changed-input list, trace and hillslope-pass locators,
and artifact hashes. The external event-pair ledger has one row per outer-joined
baseline/mutant solver-call key: scenario, hillslope, year, day, OFE, and
ordinal. Rates and peaks are metres per second, runoff depths are metres, and
durations are seconds. Baseline-only and mutant-only measurements are null on
the absent side and are distinguished by presence booleans; null never means
measured zero.

The external candidate ledger is a lossless subset or projection of generated
event-pair rows that satisfy the frozen screening flags. Candidates are
screened signals, not adjudicated mechanisms. The denominator ledger records
requested, excluded, selected, terminal, complete, failed, stopped, candidate
event, and candidate-trial counts at scenario, mutation-family, direction, and
overall grains. The prevalence summary reports numerator, denominator, and
fraction at those same grains and names whether the denominator is selected
trials, complete trials, or paired events.

The external storage manifest records every retained ledger and trial artifact
with absolute locator, byte size, SHA-256, media format, plan and selection
bindings, and retention policy. Compact committed terminal, candidate,
denominator, storage, and prevalence summaries contain hashes and sizes for
their external authorities; they do not duplicate raw traces or run decks.

All JSON is UTF-8, sorted and indented by two spaces with a trailing newline.
Canonical identifiers use sorted compact JSON. Parquet preserves full numeric
precision and nullable columns. CSV is permitted only as a convenience export,
never as the sole numeric authority.

## Additive Compatibility Rules

The execution selection may contain only records already marked `eligible` in
the frozen plan, in frozen plan order. It must contain exactly 1,088 unique IDs.
Planning is not rerun to authorize execution. The 32 excluded cover records
remain in preparation denominators and never become execution trials.

Every source read resolves beneath its declared scenario authority and every
evidence write resolves beneath the plan-specific evidence root. Symlinks in
authority, executable, selection, terminal, and evidence paths fail closed.
The observer is invoked only by a direct argument vector with `shell=False`.
No plan or manifest text is interpreted as a command.

The external generated tree is rooted at
`/home/workdir/peakflow-topanga-census-evidence/` and uses the plan-derived
locator already frozen on each trial. Trial workers never share a trial
directory. Atomic JSON replacement is the current-state boundary; preserved
attempt paths are immutable recovery evidence.

## Compatibility and Generated-Artifact Regression Checks

Before full execution, tests and dry-run evidence must prove byte-identical
selection regeneration; exact plan ID and plan-file hash; 1,088 selected unique
eligible IDs; recomputed plan totals; matching source-tree, per-input, and
executable hashes; canonical root containment; rejection of symlink escapes;
sufficient storage; and absence of current terminals at first authorization.
Dry-run resolves every selected record but launches no observer and creates no
trial run directory or terminal.

Focused tests must cover malformed and mismatched selection bindings, excluded
and unknown IDs, duplicate and reordered IDs, non-positive or excessive worker
counts, progress reconciliation, complete-terminal reuse validation, preserved
retry attempts, worker isolation, dry-run non-execution, and aggregation refusal
on missing, non-complete, binding-mismatched, or hash-mismatched artifacts. The
accepted 64-trial Phase 2A totals and representative full-precision values must
remain unchanged.

Generated-run regression checks require every selected trial to have exactly
one current complete terminal, exactly one declared changed input, and matching
trace and hillslope-pass hashes. Terminal rows must propagate to the terminal
ledger; parsed traces must propagate to the outer-joined event-pair ledger;
candidate flags must propagate to candidate and prevalence summaries; and all
scenario, family, direction, and overall totals must recompute from immutable
rows. A second aggregation over unchanged evidence must be byte-identical for
compact JSON and hash-identical for deterministic ledgers.

Before handoff, focused and broad tests, broad-exception enforcement, document
lint, scientific review, code review, QA review, and dedicated security review
must close. A scan of the plan, command record, external paths, summaries, and
reports must reject watershed, routing, channel, canopy, or LAI execution and
claims.

## Failure and Disposition Rules

Any plan, selection, authority, executable, schema, input, terminal, artifact,
path, symlink, storage, denominator, unit, event-key, null-semantics, mutation,
or screening mismatch blocks full execution or aggregation. Partial completion
never implies GO. Failed and stopped trials remain in the selected denominator
and in preserved evidence. If all selected trials cannot reach matching complete
terminals, the package publishes a NO-GO disposition instead of mutation-trial
and paired-event-row screening prevalence.

No routing or downstream-impact conclusion is permitted. Successful completion
authorizes only a local hillslope prevalence report and a screened candidate
ledger for separately governed follow-up.
