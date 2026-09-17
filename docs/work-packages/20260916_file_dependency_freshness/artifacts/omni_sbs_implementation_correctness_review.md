# S01 Omni SBS implementation correctness review

**PASS for scoped correctness after the corrections below.** Reviewed direct
orchestration, dispatcher/worker receipt propagation, clone/reset placement,
mode-copy integration and durable metadata admission after `c28f81f59`.
Independent security owns copy authority/alias fault tests. Complete generated
management/soil/WEPP artifacts, real queue execution, performance and ordinary
browse/archive acceptance remain open; this is not whole-package acceptance.

## Findings and disposition

**O-C02, high, corrected: durable refresh removed the runtime logger.**
`omni_sbs_freshness._refresh_locked` replaced the live controller dictionary with
`Omni.load_detached` state, which lacks `logger`. Actual NoDb-backed direct
execution subsequently raised AttributeError at the final compilation log; a
mixed SBS/non-SBS run failed at the next scenario log. Native execution's normal
timing/logging also requires this transient facility. The helper now restores
canonical logging with `_init_logging()` after durable refresh. This preserves
the existing external lock token while reconstituting the usable live owner.

**O-C01, medium, corrected: a legacy skip resurrected invalidated success.**
For an absent-source legacy signature, `SbsReuse` initially retained no accepted
association. Removing the entry through another real durable writer after skip
capture did not change the definition-only computed signature. Locked admission
therefore re-added the removed entry and a skipped state, despite its deliberate
invalidation. The retained initial result has `association_resurrected: true`
and no error. Reuse now deep-copies the accepted association and requires the
same association in refreshed locked state before admission, for legacy and new
receipts alike. The actual after-probe gets ESTALE and leaves the entry absent.

Two additional static compatibility concerns were corrected before their first
execution probes: RQ normalizes integer scenario8 to the SBS enum, so selection
comparison must compare equivalent SBS types without rewriting persisted
definitions; and an ineligible consumed legacy scenario must retain the original
FileNotFoundError when its required upload is missing, not substitute a generic
receipt ValueError. Actual after-controls cover both. A present source with a
legacy queued signature is still rejected rather than given an after-dispatch
receipt. The reserved receipt field is excluded from SBS definition sanitization;
non-SBS signature serialization remains unchanged.

No unresolved medium/high finding remains in this bounded correctness review.

## Retained actual evidence

The independent script is `omni_sbs_implementation_correctness_probe.py`.
All native files, controller state, logs and per-run manifests are retained under
the unique `/wc1/batch/qa-omni-correctness-*` roots recorded in its JSON files.
No named project was read or mutated. The fixtures use real Omni construction,
NoDb persistence/Redis locks, detached refresh, clone/reset, guarded copy, source
consumption and GDAL reads. Full landuse/soil/WEPP work and RQ transport are
explicit seams. No real jobs or external requests were submitted.

- `omni_sbs_implementation_correctness_probe_initial.log/.json`: five failures,
  one pass. These are two production findings above, with logger loss repeated
  in three flow controls, plus one disclosed fixture failure: the first RQ
  fixture omitted the canonical batch `runs/` component. That fixture error is
  not a production defect and is retained rather than hidden.
- `omni_sbs_implementation_correctness_probe_revision2.log/.json`: **6 passed
  in18.01s**, with module hashes unchanged during execution. Direct same-name
  class1→class3 uploads yield actual child arrays1 then3; source is consumed;
  subsequent absent-source and same-byte-touch reuse skip. Locked admission
  preserves another writer's durable unrelated field and existing run-state
  record. Mixed execution remains SBS, uniform, then dependent mulch without
  duplicate states. Failed destructive rerun retains partial work, removes the
  old child and leaves no old reusable association. Queued drift rejects before
  clone/native work while preserving the prior tree and child bytes.
- `omni_sbs_implementation_correctness_dispatch_initial.log/.json`: **3 passed
  in20.14s**. The actual dispatcher passes a verified signature through its
  existing task kwargs to the actual worker. String, integer8 and enum scenario
  types execute, consume their upload, persist their association and subsequently
  skip through the dispatcher. The queue transport records the existing
  scenario/compile/finalize sequence; a reused SBS queues only compile/finalize.
- `omni_sbs_legacy_missing_probe.log`: **1 passed in12.52s**, actual direct
  legacy year-set mismatch raises FileNotFoundError before reset and retains the
  prior association. The latest script JSON records its final helper hash and
  unchanged modules.

These phases total ten independent passing controls; they are not described as
one unchanged-revision suite. Root owns the production regression suite and
security owns the native ABA, same-file destination, observed replacement upload
and complete-set final child-guard probes. Original failures remain retained.

## Code assessment and limits

The private serialized signature carries the main-file receipt without changing
scenario names, definitions, base-loss comparison, direct year eligibility or
queue edges. A present upload is observed; consumed new identity requires its
accepted association and expected child bytes. Missing legacy identity remains
explicitly unverified. Malformed new receipts do not become legacy sentinels.

Execution validates the captured receipt before clone and again inside the
reset callback. That callback invalidates only the affected association using
fresh durable state under the existing lock. It cannot restore a failed child
generation. The passed execution object reaches mode copy and survives native
work through admission; it is not reconstructed from the resulting child.
Success/skip admission refreshes inside one lock, validates selection and input
evidence, and patches private dependency/run-state fields without nesting
non-reentrant setters. The direct loop reloads its local lists after that patch;
final SBS pruning uses current durable selection rather than reinstalling the
old whole-tree snapshot. Actual mixed-order and other-writer controls cover these
paths. Non-SBS writes keep their existing separate behavior.

The final copy/guard refinements preserve same-file rejection before truncation,
an observed-source version check after the last digest before unlink, and a final
child version check after replacement-upload observation. These are narrow
conformance changes, not atomic conditional unlink or arbitrary-writer isolation.
Inherited child sidecars remain outside this main-file receipt's proof. Reuse
does not certify the whole scientific read set or independently prove every
previous WEPP output. Normal direct/RQ generation and downstream artifact checks
must still establish the intended runtime outcome.

Final static identities (the helper's final missing-source refinement was also
exercised by the last after-probe):

```text
omni_sbs_freshness.py 6f95a6f6f3bc8836259361fb5883697578b1a2392baee5540b87b2f3961e2832
omni.py 22bd86e063d66ec94783037861b9428a30f4f2bdba6d29f1a0c816c08534e614
omni_run_orchestration_service.py e09f1b19fe75d650b04df2d272219729964774817a7c989f44fdb986c316b134
omni_clone_contrast_service.py f7490428128e0fb34a81e9e7404c71b9e098ec49c70f38097ac840b6dfc419e6
omni_mode_build_services.py 8d6d4590947eed0a731295f0f0ff7f5082af840372f98090f1a2db62ed9f518d
omni_station_catalog_service.py ecd08d23ab564e4065e5e9bcb3bdfca068063ea3db9c15dddb520855926139ae
omni_rq.py 0fca1007d49ed39ab0210ea42b90a651f752ca0bb7d828d64583e5da857924c7
```
