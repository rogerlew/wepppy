# S01 Omni SBS security checkpoint

**PASS for the refined bounded design checkpoint.** Implementation, actual
performance and whole runtime acceptance remain pending.
This is a read-only design review of `omni-sbs-freshness-contract.md` and
`omni_sbs_contract_decision.md`; no Omni implementation is approved. Reviewer:
`freshness_security`. No runtime workload was added during QA raster timing.

## Finding

**O-S01, medium, closed at draft level below: final byte equality alone does not bind
native consumption to the copied generation.** The draft requires a coherent
source copy and final child SHA comparison, but does not explicitly retain the
child's physical read guard across the native operation and locked admission.
A child can change from accepted bytes A to B, be consumed as B, then return to A;
an after-work hash can match the receipt despite outputs derived from B. The
package's actual C03/C04 change/read/restore regression demonstrates this exact
primitive failure (`raster_native_aba_initial.log` and
`raster_read_guard_security_probe_revision2.log`). This is a concrete
contract ambiguity, not a claim that an unimplemented Omni correction has
already failed a native test.

Require the copied child's resolved target and descriptor/path version guard
from the same verified copy acquisition through native work and the successful
metadata admission. Guard observable generation changes separately from the
persistent content signature, so metadata-only changes between completed runs
retain reuse. Apply the same complete observation rule to skipped work. Do not
claim isolation against arbitrary unobserved filesystem changes.

## Authority and compatibility assessment

The existing parser stores only `type` and `sbs_file_path` for SBS scenarios
(`omni_input_parser.py:53`); the signature service currently serializes every
definition field (`omni_station_catalog_service.py:219`). The reserved receipt
must be produced by verified capture, validated for exact version/path/hash
shape, and must not grant a caller-provided field authority to choose the child
path. The expected destination remains derived from the existing scenario and
selected basename. No blanket source symlink/path restriction is justified.

The actual mode copies only the main file using `shutil.copyfile`, then removes
the selected lexical source (`omni_mode_build_services.py:391`). Preserve that
source/destination access behavior and source symlink semantics. Conditional
source consumption must preserve a newer upload or replaced link. The retained
`omni_sbs_copy_boundary_probe.json` proves source `.tfw` is not copied and an
inherited child world file supplies a different transform. Consequently the
main-byte receipt is correctly limited; it does not close effective child
raster dependency freshness. Keep that separate inventory item explicit.

The existing clone resets the old child before building it
(`omni_clone_contrast_service.py:346`). Invalidating only the affected reusable
association at the actual reset boundary is necessary and appropriately scoped.
A pre-reset queued-input rejection must preserve it. The direct executor keeps
a local dependency-tree copy, while the RQ updater reloads and mutates under the
existing lock (`omni_run_orchestration_service.py:349`, `omni_rq.py:93`). Tests must
show a stale local tree cannot restore the invalidated receipt after failure,
and that a worker retries admission against current selected state under that
lock. No new whole-child rollback or queue transaction is implied.

Present-but-denied uploads cannot become consumed-source reuse. Legacy missing
source skips remain explicitly unverified; valid new consumed-source reuse
requires the accepted association plus the expected child's matching main file.
Unknown/malformed new receipts must not enter the legacy branch. Preserve direct
year-set checking, RQ's existing conditions, base-loss SHA1, names, mulch order,
non-SBS behavior and normal failed-child browse/archive retention.

## Remaining gates

Clarify O-S01, ratify measured receipt/copy budgets, then retain direct and RQ
tests for copy/selection/admission races, source replacement preservation, denied
present sources, legacy and consumed-source cases, failed reset and unrelated
scenario state. Normal disposable execution must validate the actual child SBS,
management/soil/WEPP outputs and archive/restore lifecycle. This checkpoint does
not close the separate inherited-sidecar defect or package runtime gates.

Initial reviewed document SHA-256 values:

```text
omni-sbs-freshness-contract.md 4f48be9f87e467120b24eb330dad56528826ca0977ad6848473a33d66e210d1d
omni_sbs_contract_decision.md 074cb3afa9b67e3cb16cd1ad661997e6f71343f5d38f82f3c3a14ad37d2ba0c0
```

## Refined design disposition

The revised canonical contract explicitly retains the copied main file's
physical version from verified copy through native work and locked admission,
apart from persistent content equality. It excludes the shared directory mtime
because ordinary native validation creates sibling outputs. It also states the
existing conditional-unlink limitation: preserve observable newer uploads,
without claiming atomic isolation against a write after the last check or
inventing a new shared lock. O-S01 is closed at design level. No unresolved
medium/high security design finding remains in this bounded main-file scope;
the performance checkpoint and actual implementation/runtime gates remain open.

Reviewed refinement SHA-256 values:

```text
omni-sbs-freshness-contract.md 1688fb0a9e9e415b5a674f89fbf68dd093c568cc86fde33e884bee5d82bb4049
omni_sbs_contract_decision.md 893b541cf4c5e0915694abdc104acc24460fa58267ac6b97f47ce7a7b81d9755
```

## Measured budget ratification

The final performance amendment and `sbs_receipts_profile_performance_qa.md`
support the proposed component gates without weakening read/copy/admission
guards. Two actual roughly 0.60/0.75 MB uploads and an explicitly synthetic
16.78 MB stress raster separate routine and larger-file costs. Six payload
passes in the composed copy/admission path are reported; no native execution
or actual metadata-lock result is claimed by that prototype.

Ratified for implementation: settled pre/post reuse mean 10 ms with zero digest
payload reads; cold/evicted reuse 30/200 ms real/stress; complete receipt/copy/
admission 75/650 ms. Include all real guards in final measurement and measure
actual direct/RQ native time and lock residence separately. No extra cache,
authority, lock topology, input-size restriction or reduced check is authorized
to meet a budget. This closes the checkpoint hold; it is not an implementation
or runtime performance pass.

Final reviewed SHA-256 values:

The final admission precision also correctly recognizes that the direct
properties already use separate `@nodb_setter` transactions. The intended single
admission uses the existing lock, refreshes durable state inside it and patches
only the affected private backing entries; it does not nest non-reentrant
setters or later reinstall a stale whole-tree snapshot. RQ needs the same
in-lock refresh. This preserves the canonical mutation model and closes the
review's stale-local-tree concern without adding a lock or transaction service.

```text
omni-sbs-freshness-contract.md 2738ea6abb5db62b7a7a70144847db136bface6a5abd19dc3ab0b251b2c484c9
omni_sbs_contract_decision.md 1c96e72fec259158ceff832f5e7990c0f5cd95b3d2556a767f64ea0facf62cb5
```
