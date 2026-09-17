# C03/C04 raster cache security checkpoint

Current disposition: **PASS for the revised bounded contract**, with runtime,
performance and actual implementation review pending. The original
**CHANGES REQUIRED** finding and all supporting/negative probes remain below.
No raster runtime implementation has been reviewed or approved. This review covers the draft
`docs/schemas/raster-dependency-freshness-contract.md` and
`raster_cache_contract_decision.md` at discovery base `57e60aae9` and revised
checkpoint base `36744f3b3`.

## Blocking finding R-S01 — Medium: dependency discovery can itself read remote children

The original bounded verified subset included recursively referenced VRTs, and
required native dependency discovery with no new remote lookup. Classifying
`GetFileList()` members as nonlocal *after opening the containing VRT* does not
establish that authority boundary.

Concrete evidence: `raster_discovery_security_probe_revision2.py` generates an
ordinary WarpedVRT through installed `gdal.Warp`, then points its `SourceDataset`
to a disposable loopback HTTP fixture. No external target or live project is
used. With GDAL **3.10.3**:

| Discovery stage | SimpleSource VRT control | WarpedVRT |
| --- | --- | --- |
| `IdentifyDriver` | No HTTP requests | No HTTP requests |
| `OpenEx(OF_RASTER | OF_READONLY)` | No HTTP requests | **HEAD and GET** of `source.tif` |
| `GetFileList` | Returns the `/vsicurl/` edge, no requests | Returns the edge after the two requests already occurred |

Command and output:

```text
wctl run-pytest docs/work-packages/20260916_file_dependency_freshness/artifacts/raster_discovery_security_probe_revision2.py -q -s
```

**2 passed in 1.61s.** The adjacent log and
`raster_discovery_security_{simple,warped}_revision2.json` retain each stage and
request. The initial one-case control is also retained as
`raster_discovery_security_probe.py/.json/.log` (1 passed, zero requests). That
negative result is not discarded or generalized into all-VRT safety.

### Root GTiff restriction is insufficient by itself

The parent considered narrowing verified reuse to local GTiff and letting all
other native formats run uncached. That is a compatible scope reduction, but an
actual GTiff can have auxiliary datasets that identify as another driver:

| Actual local root and companion | Root driver | HTTP at root `OpenEx` | HTTP at `GetFileList` |
| --- | --- | --- | --- |
| GTiff with WarpedVRT content at `source.tif.msk` | GTiff | 0 | **2**, HEAD + GET |
| GTiff with WarpedVRT content at `source.tif.ovr` | GTiff | 0 | **8**, source plus auxiliary probes |

`raster_discovery_security_probe_revision3.py/.log` and
`raster_discovery_security_gtiff_{mask,overview}_revision3.json` retain the
fixtures/stages. The same canonical `wctl run-pytest ... -q -s` command on
revision3 produced **2 passed in 1.71s**. These are local actual GTiff files,
not `.tif` suffixes disguising the primary VRT. The auxiliary open happens
before the observer receives its dependency list. Thus a root driver check
followed by unrestricted `GetFileList` still violates the proposed discovery
boundary. This is the same R-S01 finding, not a speculative additional risk.

Revision4 adds an internal relationship requiring no companion file: setting
`OVERVIEW_FILE` in the GTiff `OVERVIEWS` metadata domain persists a native
overview path inside the TIFF. A local primary with that domain pointing to the
loopback fixture makes **42 HTTP requests at `GetFileList`**. Identification,
driver-restricted read-only `OpenEx`, and `GetMetadata('OVERVIEWS')` each make
zero requests. Plain GTiff and plain AAIGrid with its `.prj` make zero requests.
An AAIGrid with WarpedVRT `.msk` makes two requests at `GetFileList`, matching the
GTiff auxiliary case. `raster_discovery_security_probe_revision4.py/.log` and
its four per-case JSON records retain **4 passed in 2.74s**. Do not infer from an
absence of `.ovr`/`.msk` siblings that a local GTiff has no external relationships.

Impact: opening a supported local raster for a freshness check can perform
extra remote I/O solely for discovery before the code decides the relationship
is unverified. The preexisting requested native operation may itself use that
remote source; this finding is about the draft's additional discovery authority,
not a claim that all native remote input use is unauthorized.

Required remediation to the checkpoint:

- Decide discovery authority **before native open** for VRT variants and backing
  references that may eagerly open child sources. A returned file list is too
  late for that decision. Include nested and local-ZIP-contained VRTs in that
  ordering; a local outer filename does not establish local read dependencies.
  If verified reuse is narrowed to GTiff, apply the same authority decision to
  auxiliary datasets **before `GetFileList`**, or mark uncertain companion-bearing
  layouts explicitly unverified. Root-driver-only eligibility is disproven.
  Include nonempty `OVERVIEWS` metadata in that pre-list decision; it can be
  conservatively unverified without inventing a URI/XML parser.
- An unproven/eager variant may be explicitly unverified and reach the existing
  requested native operation uncached. Preserve its selected path, options and
  native success/error behavior. This must not become a blanket VRT/VSI ban.
- Do not change process-wide GDAL network/configuration flags or install a new
  transport simply to make discovery appear local. Any bounded preinspection
  should inspect source description only, without becoming a replacement raster
  decoder or treating a suffix as evidence of driver/closure.
- Add the loopback case to implementation acceptance: discovery makes zero
  requests before the unverified disposition, while the unchanged native call
  retains its previously supported behavior. This is a finite regression, not
  an authorization to test external endpoints.

## Compatible parts of the proposal

The parent's later narrowing to local GTiff plus AAIGrid is compatible with
preserving actual large ASCII MOFE inputs and the common GTiff SBS cache.
VRT/Zarr/VSI native operations can remain uncached; no representative failing
performance case currently justifies a generalized recursive parser. For the
observed cases, the smallest eligible-discovery ordering is: local selected
path and relevant configuration; conservative ordinary companion preflight;
same-family driver validation of `.msk`/`.ovr` dependencies; read-only
driver-restricted open; `OVERVIEWS` metadata eligibility; then native file list
and verified byte observation. Opaque `.aux`/PAM XML, nondefault proxy/external
metadata settings, unsupported companions and cycles can be unverified. They
must not be omitted from a supposedly complete proof. Preserve selected/resolved
link relationships, and repeat eligibility/coherence checks on reuse. This is
evidence for a bounded design, not a complete inventory theorem for every GDAL
driver/configuration or arbitrary concurrent writer.

The content-identity correction addresses reproduced C03/C04 failures without
changing native calculations. C03 includes both selected rasters and the
existing MOFE structure digest; mapping labels are correctly applied later.
Legacy private signatures miss without migration. C04 retains its bounded
eight-entry summary cache and its existing native-only success/error boundary.
Packaged color-map data retains code/version ownership.

The retained native probes show why future verified VRT/Zarr/ZIP coverage would
need recursive membership, directory membership, selected and resolved link
edges, and backing ZIP plus external dependencies. The revised checkpoint
leaves those inputs explicitly unverified. Rechecking discovery during observation
and after materialization prevents labeling an observed old graph with a later
result. Rechecking before returning cache hits is appropriate. Byte identity
must not absorb inode/mtime into numerical equivalence; descriptor/path metadata
still governs coherent read and access checks.

Explicit unverified observations are compatible for **these numerical caches**:
no old hit is authorized, and the same native operation executes. Missing,
denied, malformed and unsupported observations need distinguishable diagnostic
reasons; they cannot become a reusable missing-file token. Failure to inspect a
directory because it lacks listing permission must not newly reject a previously
native-readable source when uncached operation succeeds. Source symlinks and
outside-run local references remain permitted under the caller's existing
authority; no new containment policy is justified.

The observer must terminate link cycles and avoid opening unrelated special
filesystem objects merely because a directory store contains them. This is an
implementation acceptance constraint, not another demonstrated flaw in code
that does not yet exist. Unknown coverage must remain unverified, never silently
complete. Discovery must stay read-only, including GDAL auxiliary metadata.

C01 finalization, C02 vector/mixed exports and C05/C06 Geneva publication remain
separate open scopes. An uncached native calculation is not evidence that a
later outside-lock publication still corresponds to its inputs. This checkpoint
must not close those findings.

## Gates remaining

R-S01 is **closed at design/checkpoint level** by the revised GTiff/AAIGrid-only
verified scope, conservative companion eligibility, restricted native driver
open and pre-list external-metadata check. Other native inputs remain accepted
and uncached. These are explicit cache-coverage decisions, not new input bans.
The evidence disproving the earlier flat/recursive/root-driver proposals is
retained; it does not approve an implementation merely for intending these
checks. No unresolved medium/high design finding remains in this revised scope.

After the standalone ancestor commit, review actual implementation for
pre-open authority, permission preservation, graph/race handling, bounded
eight-entry reuse and prior management/artifact behavior. Require actual native
C03 management-area propagation and C04 summary results, not hash-only tests.
The proposed settled/cold timing gates must include discovery/access/coherence
work and receive QA's measured acceptance. This security review does not approve
those performance or production-equivalent runtime gates.

## Exact initial eligibility recommendations

Read effective GDAL configuration rather than only environment variables. For
this bounded verified subset, treat unknown/nondefault external-discovery state
as unverified. Initial keys and ordinary defaults:

| Key | Eligible baseline |
| --- | --- |
| `GDAL_PAM_PROXY_DIR` | unset |
| `GDAL_PAM_ENABLED` | platform default YES |
| `GDAL_DISABLE_READDIR_ON_OPEN` | FALSE |
| `GDAL_READDIR_LIMIT_ON_OPEN` | 1000 |
| `GDAL_GEOREF_SOURCES` | unset/default driver order |
| `USE_RRD` | NO |
| `TIFF_USE_OVR` | FALSE |

The configuration options control sidecar visibility, proxy location,
georeferencing precedence and overview selection. Their presence does not
authorize changing them; unverified inputs still reach their existing native
operation. Recheck effective eligibility across observation. These roles/defaults
are documented in [GDAL configuration options](https://gdal.org/en/stable/user/configoptions.html)
and the [GTiff driver documentation](https://gdal.org/en/stable/drivers/raster/gtiff.html).
The latter documents PAM/internal/TAB/world/XML georeferencing sources.

GDAL caches its PAM proxy directory at first use; a later unset value alone is
not a general theorem about an arbitrary process's past configuration. The
reviewed repository search found no proxy-directory setter. This bounded design
assumes the supported static default process configuration; unknown prior proxy
configuration needs unverified treatment, not invented global mutation/reset.
See [GDAL PAM proxy documentation](https://gdal.org/en/stable/doxygen/classGDALPamDataset.html).

Companion eligibility applies to the selected lexical filename and its
extension-replaced stem, with native case variants, while retaining resolved
link identity. Opaque `.aux`/`.aux.xml` layouts bypass reuse. Recursive
`.msk`/`.ovr` inspection must apply the same driver, metadata and companion
rules before root `GetFileList`; cycles, denial or uncertainty bypass reuse.
Open eligible datasets only with `allowed_drivers=['GTiff', 'AAIGrid']` and
read-only flags, then reject coverage for nonempty `OVERVIEWS` before listing.
Do not infer local closure from a suffix or from a successful root open.

Final measured-budget amendment preserves the authority rules reviewed above.
The complete C04 hit limit is 25 ms; native-miss added mean is 50 ms. Complete
paired C03 validation limits are 75 ms settled and 400 ms cold/evicted, with whole
management/lock additions limited to 100/450 ms respectively. These finite
budgets explicitly include final companion/configuration/coherence checks and
actual 512-entry eviction pressure. No security objection to this measured
scope; prototype compositions remain evidence for budgets, not implementation
acceptance. QA owns timing validation. No authority check may be removed to pass.

Reviewed canonical SHA-256 including final configuration and measured budgets:

```text
raster-dependency-freshness-contract.md bac31a24504998816ff8b160daa1a35a23887e521bf6a84447bf74130fb135e3
raster_cache_contract_decision.md 722cea5cfab1ce7ac87ed15fc74e1403c1a92b62c3744ccafe539c8c66c80217
```

## Discovery sibling amendment checkpoint

**PASS for the revised bounded amendment**, with implementation review pending.
The original implementation's R-I01 remains retained in
`raster_implementation_security_review.md`: a vetted mask replaced before root
inventory caused loopback HEAD/GET. A later stat rejection could not prevent
that added discovery authority.

`raster_sibling_inventory_security_probe.py/.log` supplies **13 passed** actual
GDAL 3.10.3 controls. Discovery-only explicit sibling lists prevent automatic
mask/overview reopening in GTiff and AAIGrid replacement cases; all four reject
with ESTALE and zero requests. Ordinary `.prj` and world-file membership,
projection and transforms remain unchanged in the tested controls. Independently
inspected auxiliary rasters must remain in composed proof even when omitted by
the restricted root list. The numerical native operation retains its original
path/options, and no process-wide configuration is changed.

Correctness subsequently proved an initial restricted-list proposal could hide
`.tiffw` georeferencing and `.RPB` metadata. The revised amendment requires native
suffix-derived world-file names plus case variants, and rejects opaque
RPC/IMD/RRD families before restriction. Include `.rpb`, `_rpc.txt`, `.rpc.txt`,
`.imd` and `.rrd` in that conservative preflight. Retain the failed controls;
the restricted list alone is not a proof of complete dependency coverage.
Implementation must demonstrate world-file invalidation and opaque-family
bypass with original native behavior, including selected/resolved aliases.

Failure-path validation of previously recorded paths/members/configuration is
required; an inspection error must not turn observed mutation into initially
unverified/native fallback. Initially unverified inputs retain the existing
uncached native success/error boundary. These requirements address the concrete
findings without authorizing a generalized metadata parser or remote validator.

Reviewed amendment SHA-256:

```text
raster-dependency-freshness-contract.md aad6f0d1b3e71c1321af113b747d99c4686848a89ad760b2deb6d84f68f58ead
raster_cache_contract_decision.md 6cf1bda79bb12942891a05642929440dc78ba1a908cb850bc37754fa1e025df2
```
