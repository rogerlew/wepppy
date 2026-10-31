# Re-release undeployed WEPP 261029 with geometry and recession corrections

## Purpose

Deliver the user-authorized artifact revision 3 under the existing 261029 pair
names, with precise provenance and a reviewed cumulative release note. The native
fix corrects length/coefficient indexing and the recession unity discontinuity;
it does not satisfy the separate Roads sediment-magnitude objective.

## Progress

- [x] Record explicit same-name re-release authority and preserve prior history.
- [x] Candidate tests: 1073 native, 18 watchlist, 99 Disturbed, 840 Roads physical;
  twelve clean full-period replays exactly match instrumented U3 outputs.
- [x] Finish fresh Cedar semantics and independent source/particle scientific review;
  final 6,057-output parity and independent acceptance bind the dated pair.
- [x] Add all ten trigger/control seeds to permanent watchlist; incident resolved
  and hardened. Fuzzy evidence 40/40 dated executions; policy and contracts pass.
- [x] Commit native source/fixtures on verified default branch; canonical dated build
  and exact output parity verified.
- [x] Complete revision-3 sidecars; matched four-file pair atomically vendored
  with previous-identity guard. Provenance and paired host/container smokes pass.
- [x] Vendor matched pair and verify provenance, paired host/container execution,
  fresh generated outputs and discovery/readers; 142 targeted tests pass.
- [x] Complete isolated application regression coverage: 12,536 passed / 367 skipped;
  failed initial attempts retained and excluded, successful coverage counted once.
- [x] Finalize and independently review cumulative report revision 3 (20pages,
  eight figures); published exact PDF/manifest and verified HTTP/navigation.
  Earlier issued report bytes unchanged.
- [x] Retain native evidence, update accepted ADR/contracts/user documentation and
  both trackers. Final native archive verifies 41,613 files; delivery archive
  verifies 984 files. Independent application acceptance closes the final gate.

## Surprises & Discoveries

EPLANE's one-based dummy shifted the zero-based caller's lengths relative to
hydraulic coefficients. Homogeneous tests concealed it. The source repair passes
all eight independent integral probes; released source passes two. QINF's extra
unity cutoff disagrees with its continuous documented FTEST branches. The combined
repair eliminates observed negative linked total FIN/unfunded requests in all
12 full-period target/control cases. Roads magnitude nevertheless worsens overall.

## Decision Log

2026-10-31, user: replace undeployed 261029 and update release note, preserving
version names. Codex: use artifact_revision=3 and report revision 3, retain older
bytes/reports, preserve defaults and deployment boundary. Reuse independently
authorized scientific, implementation and publication reviewers.

## Outcomes & Retrospective

Artifact revision 3 replaces the undeployed same-name matched pair. Final native
and scientific gates pass; actual vendored provenance, four smokes, 142 targeted
tests and fresh hillslope/watershed readers pass. Isolated application coverage:
12,536 passed / 367 skipped. The reviewed 20-page/eight-figure report and manifest are
published and actual local HTTP hashes/MIME/navigation verified. Older reports
remain unchanged. Native delivery is pushed (`eb601ce8d`); WEPPpy delivery is
scoped to this release and its retained Roads evidence.

Roads magnitude remains unmet (744/840 versus 749/840 previously); no parameter
candidate is adopted. No production deployment, default switch or UI implementation.
Toolchain PATH must pin binutils as well as compiler; final dated outputs were
rerun rather than inferred from research-binary parity. Complete-pair staging
must precede consumers, and Unix-socket tests require short temporary paths.

## Context and execution

WEPPpy root is /workdir/wepppy; native default checkout is
/workdir/wepp-forest-release-20261009, expected branch
wepp_260430_negmeltfix_comparator. Verify origin/HEAD rather than assuming branch.
Native active package: docs/work-packages/20261031-roads-open-boundary-funding.
Raw evidence: /workdir/wepppy/out/roads-native-funding-20261031. Frozen candidate
source: D2-frozen-source; receipt D2-candidate-build.json in native artifacts.
Released revision-2 watershed SHA is
819b91721f67c4a86a5ecea14c5beb840e9a705025da2a2cedf2b97a5e067715;
hill SHA is 21d8480041d2efed942abb8471271ce1a11c5f72190d45c0c42dbe0028c019ed.
Back up both native release and vendored four-file pairs before replacement.

Use tools/build_wepp_dated_release.sh with TARGET_TAG=261029 and system compiler
on committed source. It builds sequentially; concurrent targets race shared
capacity includes. Restore watershed includes after hill build. Confirm original
capacity profiles and run smoke, watchlist, artifact policy and pytest as required
by native AGENTS. No parameter or guard-tolerance changes are authorized to pass.

Scientific gate includes frozen twelve-case U2/U3 factorial, D1 reference domain,
matched local accounting, full native gates and fresh Cedar 864-hillslope/24-year
outputs with independent nine-file observer parity and intermediate/source checks.
The existing Roads 840-case development replay retains all seven generated-soil
materials, reference hashes and original magnitude criteria; no withheld outcomes.
Magnitude failure must be disclosed separately from native bug-fix acceptance.

Preserve sidecar capabilities and record exact source branch/commit, artifact
revision, matched pair hashes, earlier identities and tests. Stage complete files
then atomically replace each binary/sidecar. Run tools/check_wepp_binary_provenance.sh,
both host/container smokes and wctl runner/discovery/output tests after vendoring.
Run required application sanity via wctl; isolate concurrent unrelated changes
if needed using an existing checkout or detached worktree, without switching branches.

Report source: native docs/release-notes/wepp_261029, separate main-r3.tex and
identity include/register/figures. Follow AUTHORING.md, retain r1/r2 byte identities,
use original prose/equations and reviewed figures without restricted source listings.
After scientific/implementation/disclosure acceptance, publish revision-3 PDF and
manifest into existing WEPPpy static report directory and update existing usersum
navigation/changelog. Validate actual served artifacts, MIME and hashes.

## Recovery and handoff

Any failed native scientific invariant blocks vendoring; retain and diagnose it.
Do not change frozen tolerances or omit cases. Preserve previous four-file pair
for reversible restoration before consumers run if post-vendor checks fail.
Do not overwrite earlier archive/report editions. Final handoff names installed
hashes/revision, tests, published note and remaining Roads magnitude/UI work.

Revision note (2026-10-31): final native/scientific gates accepted. Canonical
builds pin system binutils as well as compiler; final outputs were rerun after
research/canonical ELF differences. Application testing uses an isolated committed
base. A partial staging attempt was rejected and excluded; a mocked-deployment
timeout is retained while its entire unchanged shard is replayed.
