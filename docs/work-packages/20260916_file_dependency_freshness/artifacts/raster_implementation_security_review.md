# C03/C04 implementation security review

**PASS for the final reviewed C03/C04 implementation.** R-I01, R-I02 and R-I03
are closed by the retained actual after-probes below. The original findings,
superseded approval and failed evidence remain documented. Runtime and
performance acceptance remain pending.
This is scoped to the implementation after checkpoints `ceb715c08` and
`308f9edee`: `all_your_base/raster_freshness.py/.pyi`,
`nodb/core/landuse.py` and `nodb/mods/baer/sbs_map.py`.
Reviewer: `freshness_security`. No production/test edits or benchmark loads.

## R-I01 — Medium, closed: automatic auxiliary reopening after preflight

The original implementation recursively verifies a real GTiff mask before
opening the root GTiff. Replacing that mask with a local WarpedVRT immediately
before root `OpenEx` makes `GetFileList` issue **HEAD + GET** to its child before
returning the remote dependency. The observer then classifies membership as
unverified. The first probe returned `None` without ESTALE because that branch
preceded final observation validation. No cached result was accepted, but the
freshness observer had already performed additional remote discovery.

This is an actual observation-time filesystem replacement, not a hypothetical
write after final validation. The deterministic hook schedules `os.replace`
around actual native opens; file types, GDAL discovery and HTTP requests are
real. All traffic targets a disposable loopback server; no external target or
named project was used. The numerical native operation was not invoked in this
failure case, so the two requests belong entirely to new discovery.

Evidence: `raster_implementation_security_probe.py/.log` and
`raster_implementation_security_preflight_replacement.json`. The run has
**18 passed in 13.19s**: its final assertion characterizes the defect and is not
an acceptance assertion. Preserve this baseline when adding the corrected case.

The parent's subsequent failure-path validation preserves observed generation
drift as ESTALE, including unavailable recorded members and changed effective
configuration. That addresses the downgrade component. A later version check
cannot retract an already issued request, so it does not alone close R-I01.

## R-I02 — Low, closed: unavailable observed parent had a raw access/path error

`raster_observation_error_security_probe.py/.log` retains three actual changes
after hashing. Source removal produces ESTALE as intended. Renaming an already
enumerated parent produces ENOENT; denying its permissions produces EACCES.
The `_companions` call in `validate` raises before the unavailable-version
translation. All three reject the observation, so this is error-contract
conformance rather than false-current acceptance. Translate failure to validate
previously recorded companion membership into ESTALE, while preserving initially
unlistable directories as unverified so native-readable inputs remain usable.
The **3 passed in 1.09s** run characterizes current error types, not their closure.
The parent's narrow validation wrapper was independently verified by
`raster_observation_error_security_probe_revision2.py/.log`: **3 passed in
1.08s**, explicitly requiring ESTALE for source removal, parent rename and
parent denial. Initial error records remain retained. Initial-access compatibility
will be rerun with the final observer.

## Passing initial boundaries

Seven stationary remote layouts return unverified with zero requests: root
WarpedVRT, GTiff mask/overview WarpedVRT, internally stored OVERVIEW_FILE,
resolved-target mask behind a source alias, uppercase stem mask, and AAIGrid
mask. Effective thread-local nondefault values for each of the seven configured
keys bypass discovery before `OpenEx` and remain unchanged. Same-byte source
alias retargeting changes the proof through resolved identity.

Under the actual container UID 1000, a source made unreadable after a successful
summary does not return the old cached result: wrapper and direct native call
raise the same error. An execute-only source directory prevents observer
listing, but the original native summary still succeeds uncached with the same
value. These checks preserve the distinction between unproven inspection and
native input permission. Initial absence, unproved native formats and errors
must keep that behavior after the failure-path refinement.

C04 admits its bounded LRU value only after the internal post-check, with a
separate check on hits. C03 compares the complete paired signature before
installing counts, stages management values, and copies reused runtime-generated
summaries. Independent correctness review and actual generated-output tests
remain responsible for full mutation/noninterference coverage.

## R-I03 — Medium, closed: changed then restored bytes admitted an intermediate result

The root's actual native regression
`tests/test_raster_freshness.py::test_changed_then_restored_native_input_is_not_admitted`
changes a GTiff from class 1 to class 3, calls the real native summary, then
restores the original bytes and mtime before returning. The pre/post content
proofs agree even though the native result consumed class 3. The expected
ESTALE assertion fails in `raster_native_aba_initial.log`; this is a confirmed
ordinary filesystem/native-read case, not a fabricated stat-key collision or
a write after final validation.

Keep strict generation read guards across native computation and cache-hit
validation, separately from the content/LRU key. Capture/bind those guards with
the verified observation rather than assigning later path metadata to an older
proof. Cover recorded members and companion/selection contexts; C03 needs the
complete two-raster set. C04 must check before the cached function can admit its
result, with an outer guard for hits. Completed same-byte metadata operations
between calls must still preserve numerical cache identity. This restores the
existing coherence contract; it does not authorize a new scientific identity or
promise arbitrary concurrent-writer isolation beyond observable generation
checks. Re-run the actual failing regression and independent read/access cases
before restoring implementation approval.

The correction uses frozen `RasterDependencyObservation`: content signature is
its equality/hash identity; `read_guard` is explicitly excluded from both.
The guard captures file/resolved identities, companion-parent directory versions
and effective configuration in the **same validated acquisition**. C03 compares
the complete set across counting. C04 compares before LRU admission and again
across hit return. Content-only convenience functions remain available but do
not claim to guard a native materialization interval.

`raster_read_guard_security_probe_revision2.py/.log` independently verifies
**3 passed**: actual class 1→3 native read→restored class 1 raises ESTALE with
zero LRU admission; transient companion-directory mutation raises ESTALE; and
completed link/unlink/chmod operations retain equal content/hash identity with
one native call and an actual cache hit. The initial independent combined run
retains **1 failed, 23 passed** in `raster_read_guard_security_after.log`: the
failed reviewer assertion assumed temporary PAM nodata would change this native
summary, but actual output stayed equal. Directory drift was correctly rejected.
That negative scientific result is retained and is not presented as another
numerical defect. Only that characterization assertion changed in revision2;
the other 23 authority/access/error cases passed against the guard implementation.

## Smallest evidenced amendment proposal

`raster_sibling_inventory_security_probe.py/.log` evaluates GDAL's existing
`sibling_files` argument without changing production code. **13 passed in
5.25s** with installed GDAL 3.10.3:

| Actual case | Requests with bounded sibling list | Result |
| --- | ---: | --- |
| GTiff or AAIGrid, stationary WarpedVRT at `.msk`/`.ovr` | 0 | Unverified before native open |
| Same four combinations, vetted GTiff auxiliary replaced before root open | 0 | ESTALE; no automatic auxiliary reopen |
| Plain GTiff, AAIGrid plus `.prj`, actual GTiff world file | 0 | Same native file list, projection and transform |
| Local GTiff mask or overview | 0 | Root list omits auxiliary as intended; geometry unchanged |

Proposed canonical refinement: each **discovery-only** `OpenEx` receives an
explicit list containing the selected source basename and its preflight-proven
ordinary sibling names. Exclude `.aux`, `.aux.xml`, `.xml`, `.msk` and `.ovr`
from automatic sibling discovery. Apply this recursively to auxiliary raster
inspection. Keep each independently proven auxiliary and its selected/resolved
edges in the composed graph and content observations, even though the restricted
root `GetFileList` no longer reports it. Ordinary dependencies remain observed
and hashed; unsupported companions still make the layout unverified.

This option change belongs in the canonical contract and an independently
reviewed ancestor amendment before implementation. It does **not** change the
options or path of either numerical native operation, disable masks/overviews in
the calculation, mutate global GDAL configuration or create a snapshot/cache
service. Existing configuration/metadata eligibility, companion rediscovery,
access checks, failure-path version validation and pre/post consumer checks all
remain required. The probe supports this finite GTiff/AAIGrid boundary, not a
universal GDAL configuration or concurrent-writer isolation claim.

The first sibling-list proposal hid native `.tiffw` and `.RPB` members in real
correctness controls. The revised amendment adds suffix-derived world-file
names/case variants and excludes opaque RPC/IMD/RRD layouts before restriction.
The correctness review's seven-case amendment seam passes, including arbitrary
GTiff filename extensions and actual RPC creation. The checkpoint security
artifact records scoped amendment PASS and exact document hashes. This does
not substitute for implementing or independently verifying the final helper.

## Final actual implementation verification

The amended helper supplies restricted siblings itself; the final authority
probe only schedules replacement and checks actual passed options, without
injecting its own sibling restriction. `raster_sibling_inventory_security_probe_revision2.py/.log`
retains **13 passed in 5.23s**. All four actual GTiff/AAIGrid mask/overview
replacements make zero requests and raise ESTALE. The original initial
replacement that issued HEAD/GET remains in its separate artifact.

`raster_security_after_implementation.log` records **21 passed in 13.40s** from
the revision2 implementation and observed-error probes: stationary remote
refusal, effective thread-local configuration, same-byte alias retargeting,
real file denial, native success through execute-only directories, zero-request
replacement rejection and all three unavailable-observation ESTALE cases.
Source/sidecar symlink support and numerical native options remain unchanged.
These after-probes close R-I01/R-I02. They predate the distinct R-I03
reproduction; R-I03 closure is recorded separately above.

Reviewed source SHA-256 values:

```text
raster_freshness.py 7e218d1e7ec5e4da55914e8bbfd695dd423a2d1ae890afd87baf343761f80b24
landuse.py 46954d6d325789972af2ad901458c3106f5d88dde1212715fd409baba5012cd8
sbs_map.py 5212036fa8357987b65c7add0da435a1b4a95f26b510b18b44eba075cd4242b7
```

## Remaining gate

QA must measure the complete
final implementation with all guards; none of these small probes establishes
whole-consumer timing, management/WEPP propagation or restarted-stack acceptance.
C01, other raster publication and PF-R01 dispositions remain separate.
