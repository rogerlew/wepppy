# S01 SBS main-file receipt checkpoint

Status: draft; no implementation. Canonical intended contract is
`docs/schemas/omni-sbs-freshness-contract.md`. Existing Omni README dependency
tracking is the current owner and must link/update at checkpoint. Upload/native
SBS/RQ response/NoDb authority remains unchanged.

## Compatibility and rationale

Actual upload→parser→direct gate reuses class1 after same-name class3 upload;
worker path has the same missing byte identity. Existing native copy removes
limbo main and retains destination sidecars. Therefore hash-in-filename and
always-hash-absent-source proposals regress existing names/consumed-source reuse;
hashing source-sidecars would falsely describe the child. Add private version1
main receipt within existing signature, bind actual copy and admission, preserve
legacy missing-source skips explicitly as unverified history. No added public
fields, queue edges or table columns.

An old dependency association must be invalidated at actual destructive reset,
not on pre-clone queued-drift rejection. Otherwise a failed replacement can later
skip as legacy success. This narrowly changes reusable metadata for the affected
scenario; retain existing error/audit files and do not claim whole-child rollback.

Independent retained proposal and actual copy-boundary probe are
`omni_sbs_content_correctness_proposal.md` and
`omni_sbs_copy_boundary_probe.py/.json/.log`. Native inherited-sidecar equivalence
remains explicitly outside the main-byte correction. Need independent reviews,
representative cost gate, direct/RQ regression and full generated-child runtime
acceptance before closeout. No implementation is authorized by this draft alone.

Review precision: carry the verified copied-main physical version through native
work and locked admission, separate from receipt content; reject observed ABA.
Normal native work creates sibling outputs, so a shared directory timestamp is
not this read guard. Existing upload/copy paths do not share conditional-unlink
serialization: preserve observed newer uploads, explicitly excluding arbitrary
writes after the last check. No new lock topology is authorized by this scope.

Direct persistence precision: `OmniStateContrastMixin` supplies
`@nodb_setter` properties for both scenario dependency and run state; they are
not raw unguarded assignments. Each setter locks/dumps independently, however,
so receipt validation outside them is not one admitted metadata operation.
Group the affected SBS entry and run-state record in one existing NoDb lock,
refreshing durable state inside it before validation and private-field patches.
The setters themselves are not reentrant and must not be nested under that
lock. RQ currently refetches before its lock; the new SBS admission must refresh
inside it as required by the canonical NoDb concurrency contract. Preserve
unrelated refreshed entries, direct ordering and initial state-reset semantics;
subsequent cleanup must not reinstall a stale whole-tree copy. This is bounded
admission conformance, not a new lock/service or whole-orchestrator transaction.

## Measured performance decision

Root and independent QA accept the measured component gates in the canonical
contract's "Performance acceptance" section, pending correctness/security
ratification of this checkpoint. Actual 0.60/0.75 MB uploads and a labeled
16.78 MB valid TIFF stress fixture were used only after ordinary copying into
unique disposable paths. Evidence is `sbs_receipts_profile_performance_qa.md`
and `sbs_receipts_profile_performance_baseline.json/.log`.

Settled pre/post receipt reuse measured 0.44–1.21 ms with zero payload reads;
helper-cold reuse measured 5.91–6.70 ms real /112.23 ms stress. The composed
initial receipt/copy/consume/two-admission component measured 29.28–34.55 ms real
/459.48 ms stress, including six payload passes. Ratify mean gates of 10 ms
settled reuse, 30/200 ms cold or evicted reuse, and 75/650 ms complete receipt/
copy/admission for real/stress fixtures. This headroom accommodates final guards;
it does not authorize omitting them.

Existing native copy/consume measured 7.92–9.17/88.99 ms. Native validation,
landuse/soil/WEPP execution and actual metadata-lock acquisition were excluded
and must be reported separately in final actual direct/RQ acceptance. No new
cache or lock topology is justified by these costs; no upload limit is imposed.
The prototype and existing-path timings are not a pass for unimplemented code.
