# S01 Omni SBS checkpoint: independent correctness review

**Current disposition: PASS for the revised bounded checkpoint; implementation
and runtime gates remain pending.** Production and tests were read-only. This review covers the
bounded main-file receipt, not inherited raster closure or whole-child rollback.

## Findings

| ID | Severity / disposition | Required treatment |
| --- | --- | --- |
| OS-C01 | Medium, draft precision required | Carry the physical version of the verified copied child main through the entire native execution interval and locked success admission, separately from the content receipt. SHA equality before and after is insufficient when native work reads temporary changed bytes and the original bytes return before admission. The actual C03/C04 old/new/old reproductions establish this mechanism. Retain the same-acquisition guard rather than taking an unrelated later stat. |
| OS-C02 | Concurrency limit to state explicitly | The existing Omni upload writer and `omni_mode_build_services.py` copy/delete branch have no shared writer lock. A pre-unlink identity check protects observed replacement but does not make check-plus-unlink atomic against replacement after the check. Do not claim unconditional preservation of every overlapping same-name upload from this bounded change. If a stronger guarantee is required, first demonstrate the smallest existing serialization boundary; do not silently add a protocol. |
| OS-C03 | Gate pending | No representative receipt/copy/admission budget has been measured and ratified. This review cannot authorize the implementation checkpoint without that gate. |

For OS-C01, guard the copied main file, not its whole parent directory: ordinary
`Disturbed.validate` creates WGS/display/four-class siblings in that directory.
The native read-set limitation for inherited masks/world files/PAM/IMG companions
must remain explicit. Main-only validation must not claim to resolve that closure.

## Supported flow and state assessment

The retained actual upload/parser/direct-orchestrator probe establishes same-name
class 1 to class 3 reuse incorrectly skips the second execution. The actual SBS
copy probe separately proves the source main is consumed and destination-side
world files affect the child. Adding bytes to the existing private signature is
therefore appropriate; renaming public scenarios, hashing only limbo sidecars or
requiring the limbo source forever would change working behavior.

Preserve direct execution's year-set condition and RQ's existing criteria. The
worker already accepts a signature argument, so carrying the captured receipt
does not require a queue edge. New absent-source reuse must validate the expected
child destination derived from the scenario definition, never a receipt-chosen
path. Missing-source legacy skips remain explicitly unverified. Malformed new
receipts must not take that legacy branch. Present input with a legacy signature
must execute to establish actual copy provenance.

Invalidation at actual destructive child reset is necessary: RQ reuse does not
have the direct service's output-year guard, so retaining an old successful
association after a failed replacement could revive it. Reject queued drift
before reset while preserving the association; clear only the affected reuse
association once destructive work starts. Do not manufacture success provenance
from whichever child files remain after failure.

The reserved `_sbs_content` object must be implementation-owned, validated with
exact version/type/keys, and excluded from any user-supplied definition fields
before construction. Preserve non-SBS signature bytes and parameter semantics.
Source access failures must propagate through the existing direct/RQ boundaries;
no permission failure may be interpreted as the consumed-source sentinel.

## Implementation and acceptance constraints

Use the existing copy destination and permission behavior. Bind opened source
bytes to captured receipt and copied child bytes before native validation; retain
the child generation guard through model work. Post-check selection, any present
new upload, main bytes and physical guard before and inside metadata admission.
Metadata-only changes between completed requests may reuse after content checks;
physical drift within a computation must reject. Skips need their own matching
post-observation.

Actual direct and RQ tests must cover consumed-source reuse, equal-byte new upload,
legacy/new malformed receipts, queued drift before reset, failed destructive
rerun, observed copy/delete replacement, native old/new/old change, and normal
non-SBS/mulch ordering. Native child management/soil/WEPP generation and archive
retention remain runtime acceptance requirements, not claims of this review.

Reviewed initial draft identities:

```text
omni-sbs-freshness-contract.md 4f48be9f87e467120b24eb330dad56528826ca0977ad6848473a33d66e210d1d
omni_sbs_contract_decision.md 074cb3afa9b67e3cb16cd1ad661997e6f71343f5d38f82f3c3a14ad37d2ba0c0
```

## Revised design disposition

The revised canonical draft resolves OS-C01 by retaining the verified copied-main
physical guard throughout native work and locked admission, explicitly excluding
the intentionally changing sibling directory. OS-C02 now states the actual
pre-unlink observation limit and does not claim atomic conditional deletion.
**The bounded correctness design passes; OS-C03 remains pending, so this is not
approval of an implementation checkpoint or runtime acceptance.**

```text
omni-sbs-freshness-contract.md 1688fb0a9e9e415b5a674f89fbf68dd093c568cc86fde33e884bee5d82bb4049
omni_sbs_contract_decision.md 893b541cf4c5e0915694abdc104acc24460fa58267ac6b97f47ce7a7b81d9755
```

## Final lock and measured-budget ratification

Actual inheritance tracing found both state setters at
`omni_state_contrast_mixin.py:91–106`, decorated with `@nodb_setter`;
`Omni` inherits that mixin at `omni.py:715`. `base.py:nodb_setter` enters
`self.locked()` unconditionally, so nesting those setters under an outer lock
would raise `NoDbAlreadyLockedError`. The direct service currently persists the
dependency tree and run-state list in separate setter transactions, while RQ's
`_update_dependency_state` refetches before acquiring its explicit lock. Neither
placement alone is the intended grouped SBS admission. The revised canonical
paragraph now requires one existing lock, in-lock durable refresh, fresh
selection/receipt validation and scoped private-field patches, preserving
unrelated state and ordering. It also forbids a later stale whole-tree overwrite.
This matches the canonical NoDb concurrency contract and the local
`Omni.reset_for_fork` in-lock detached-refresh precedent; no new lock topology is
introduced. Regression coverage must exercise other-entry updates during native
execution, grouped persistence and non-reentrant setter avoidance.

OS-C03 is now resolved **at checkpoint level** by the retained independent
`sbs_receipts_profile_performance_qa.md` measurements. The two real 599/747 KB
uploads and labeled 16.78 MB stress TIFF support 10-ms settled receipt reuse
(zero payload reads), 30/200-ms real/stress cold or actually evicted reuse, and
75/650-ms complete receipt/copy/admission components. The prototype performed
six main-file passes and measured 29–35/459 ms for copy/admission; it omitted
native work and actual metadata-lock acquisition explicitly. Final implemented
direct/RQ paths must remeasure all checks, hydration/persistence and lock
residence separately rather than treating this composition as a runtime pass.
No larger-file policy, cache redesign or scientific change is justified by it.

**Final scoped checkpoint: PASS**, with security ratification separately owned.

```text
omni-sbs-freshness-contract.md 2738ea6abb5db62b7a7a70144847db136bface6a5abd19dc3ab0b251b2c484c9
omni_sbs_contract_decision.md 1c96e72fec259158ceff832f5e7990c0f5cd95b3d2556a767f64ea0facf62cb5
```
