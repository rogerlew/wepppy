# C03/C04 implementation security review

**CHANGES REQUIRED: R-I01 remains open pending a reviewed discovery amendment
and its actual implementation.** This is scoped to the uncommitted implementation
after checkpoint `ceb715c08`: `all_your_base/raster_freshness.py/.pyi`,
`nodb/core/landuse.py` and `nodb/mods/baer/sbs_map.py`.
Reviewer: `freshness_security`. No production/test edits or benchmark loads.

## R-I01 — Medium: automatic auxiliary reopening after preflight

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

## Remaining gate

Review the final amended observer and rerun the real replacement case with zero
requests as an acceptance condition. Include alias/ordinary-companion discovery,
absence/denial, post-failure ESTALE and unchanged native result behavior. Bind the
final source revision and retain the baseline. QA must measure the complete
final implementation with all guards; none of these small probes establishes
whole-consumer timing, management/WEPP propagation or restarted-stack acceptance.
C01, other raster publication and PF-R01 dispositions remain separate.
