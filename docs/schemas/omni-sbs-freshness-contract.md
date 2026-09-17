# Omni SBS scenario input freshness

Status: intended bounded S01 behavior; checkpoint pending.

## Scope and identity

Preserve scenario names/paths, ordinary definitions, base-loss SHA1 comparison,
direct execution's existing year-set condition, queue ordering and numerical
operations. SBS scenario reuse additionally binds uploaded main-file bytes;
non-SBS signatures remain unchanged. This correction does not certify inherited
child raster sidecars or change stream-pruning completion receipts.

Keep the existing serialized private`signature` string. For SBS, add a reserved
`_sbs_content` object to its sanitized definition with exactly version1,
source_path (the selected path already present in the definition) and sha256.
It describes the main bytes copied to the existing scenario child's
`disturbed/<selected-basename>`, never an arbitrary receipt-selected destination.
The definition stored for the user is unchanged; no hash is added to the public
scenario name. Use the existing verified ordinary-file SHA helper and preserve
source symlink/programmatic-path authority and read access on every observation.

A present selected upload must be read and compared even if a prior success
exists. Changed bytes at the same path miss reuse. Same bytes with metadata-only
changes retain reuse when the other existing conditions match. Failed access,
malformed/new unknown receipts or changed observations cannot match a reusable
missing sentinel or silently fall back to an older child.

## Consumed uploads and legacy behavior

Successful SBS mode historically deletes the limbo source after copying. New
accepted receipts can reuse a consumed-source scenario only through its existing
accepted association and a matching expected child main file. Verify the copied
file; do not fabricate a receipt from today's child. If execution is needed but
the required upload is absent, preserve the existing missing-source failure.

Legacy definition-only success with an absent source keeps its existing skip
eligibility, explicitly without historical byte proof. A present upload requires
actual execution to establish a new receipt, even if legacy definition/loss
metadata match. Malformed/unknown new receipts are not legacy. Older readers
conservatively miss the added signature; no public key/column migration is
required, and rollback must not claim historical byte identity.

## Execution, copy and admission

Carry the captured receipt through the existing direct/queued execution path.
Reobserve before clone/reset; queued input/selection drift rejects before the
existing destructive workspace replacement. At the actual reset boundary,
invalidate only this scenario's old reusable dependency association, so failed
work cannot resurrect legacy success over a partially replaced child. Preserve
prior association when rejection occurs before reset. Existing child reset is
not atomic generation publication; no rollback of all prior outputs is claimed.

Copy bytes from the captured opened source, compare descriptor/path version and
resulting child main bytes with the receipt, and delete only the still-matching
consumed source. An observed newer same-name upload must not be blindly removed. No existing
shared upload/copy lock provides atomic conditional unlink; the check protects
observable pre-unlink replacement, not a writer racing after the final check.
Do not claim stronger isolation or add a new locking protocol in this correction. Preserve
source access, destination mode/write behavior and existing native validation.
Retain failures in the normal child browse/archive lifecycle.

Capture the copied child's opened/selected physical file version after verified
copy and retain it across native work through locked admission, separately from
the persistent content receipt. Reject observed changed-then-restored bytes;
final SHA equality alone is insufficient. Do not guard the shared child directory
mtime: normal native validation intentionally creates sibling outputs.

After native work and before success metadata, verify the copied child main
against the captured receipt and recheck the current selected definition and any
present replacement upload. Repeat the applicable admission check inside one
short metadata transaction, for both direct passes and the RQ worker. Acquire
the existing NoDb lock, refresh durable state while holding it, validate the
current scenario selection and receipt, and patch only the affected dependency
entry and its run-state record. Preserve unrelated refreshed fields and direct
execution ordering/state-reset semantics. Direct assignments currently use two
separate `@nodb_setter` transactions; they do not group admission with both
records. The grouped transaction updates their private backing fields rather
than invoking those non-reentrant setters under an outer lock. RQ's existing
transaction likewise needs its mutation base refreshed inside the lock, not
only a `getInstance` call before acquisition. Do not later reinstall an older
whole dependency-tree snapshot over the refreshed scenario patch. A cache skip
also requires a matching post-observation before recording skipped.
Never compute a new after-the-fact receipt for whichever child happens to exist.
Standalone scenario execution may capture its own input receipt; orchestration
must bind its existing scenario selection and passed receipt. No new queue edge,
service, database or generalized execution transaction is authorized.

## Limits and acceptance

Only the selected main file is copied; source-sidecar hashing would not describe
what the child reads. Inherited destination masks/world files/PAM/IMG companions
remain a separately documented unresolved native-dependency boundary. Native
validation and calculations continue to inspect the existing child context.
Do not claim this main-byte receipt proves the whole SBS scientific read set.

Cover same-name1→3 upload, equal bytes, consumed source, legacy and malformed
receipts, denied present source, queued drift, copy mutation/new-upload
preservation, native-to-admission drift, failed destructive rerun and untouched
non-SBS/mulch ordering. Validate actual child SBS, generated management/soil/WEPP
artifacts and browse/archive retention through disposable normal execution.
The representative pre-implementation cost gate is defined below. Actual
implementation and normal direct/RQ native runtime acceptance remain required.

## Performance acceptance

The reviewed local fixtures are actual 599,196-byte and 747,242-byte SBS uploads,
plus a labeled 16,779,862-byte uncompressed TIFF stress fixture derived from
copied class pixels. These are mean component budgets on warm filesystem pages,
not cold-storage guarantees or a new upload size limit. Retained evidence and
rationale: the work package's `artifacts/sbs_receipts_profile_performance_qa.md`
and `sbs_receipts_profile_performance_baseline.json/.log`.

The complete pre/post receipt reuse component must average at most 10 ms once
settled, with zero digest payload reads; helper-cold or actual 512-entry eviction
must average at most 30 ms on each real fixture and 200 ms on the stress fixture.
The complete initial receipt, verified copy/consume and required admission-check
component must average at most 75 ms real and 650 ms stress. Include every actual
implementation check; the measured prototype is not an implementation pass.

These gates exclude clone/reset, native SBS validation, generated landuse/soil/
WEPP work and metadata-lock acquisition. Final acceptance must measure actual
direct and queued operations, report whole native runtime and lock residence
separately, and account for all receipt checks performed inside the lock. Do not
relax required guards to meet the gate. Larger supported inputs need additional
size-aware observation; this correction imposes no new file-size policy.
