# WEPP 261029 artifact revision 2

Status: closed 2026-10-31 UTC. The owner confirms 261029 has not deployed and explicitly requests
re-releasing the same named matched pair in WEPPpy and updating the release note.
This authorizes replacing the undeployed revision 1 binaries/sidecars; preserve
old hashes, issued PDF revision 1 and closed release work-package history.

See [the completed plan](prompts/completed/rerelease_execplan.md) and
[tracker](tracker.md). Native investigation remains in
`wepp-forest-release-20261009/docs/work-packages/20261030-roads-native-accounting`.
U10 is independently accepted and vendored with complete revision 2 metadata.
The reviewed report is published alongside revision 1; actual local HTTP hashes
and navigation pass. Native validation passes 1,059 tests, 840 Roads physical
cases, 99 Disturbed tests and 18 watchlist cases. Fresh Cedar class-sign, particle,
water and source audits pass. Post-vendor provenance, host/container smokes,
69 targeted tests and selected hill/watershed reader checks pass. The full WEPPpy
coverage passes in segments: 12,213 passed and 332 skipped across all 12,545
collected tests. Earlier failures and their bounded resolutions are retained; this
is not a claim of one uninterrupted green run. All 14 raw-evidence archives are
verified. Native release delivery is `0df4c9227`; WEPPpy delivery is scoped to
this release and excludes concurrent request-handling changes.

Deployment, default selection changes and Roads UI implementation are outside
this release scope. Roads magnitude acceptance remains unmet: 719/766 meaningful
and 30/74 small-reference cases pass. See [the final scientific review](artifacts/U10-Yalin-independent-scientific-review.md)
and [integration gates](artifacts/integration-gates.json).

## Acceptance and compatibility

Use a matched default-branch Linux pair and accurate artifact_revision=2
sidecars. Validate exact equivalence to the scientifically accepted candidate,
provenance, host/container smokes, discovery/selection and actual generated output
reader behavior. Regenerate all contributing hillslope/PASS/watershed artifacts:
the same binary filename does not imply the same executable bytes. Preserve
capabilities, banner, capacity profiles and existing pass-family/schema contracts.
Document shared effects outside Roads and remaining scientific limitations.

Keep revised PDF outside public static storage until scientific, implementation
and disclosure review passes; then publish with its revisioned filename/manifest
through existing report navigation and verify HTTP content type and downloaded
hash. Preserve original report files. The user's explicit update request provides
authority to publish the reviewed revision; no additional permission checkpoint
is inferred from the previous report's approval workflow.

Security impact: low; existing execution/publication paths and identities only.
No dedicated security review is required. Complexity budget: existing build,
sidecar, vendoring and report tooling; no new infrastructure or dependencies.
Scientific and correctness review artifacts are required. Native source/ADRs
0113–0118 record parameterization rationale; Roads magnitude acceptance and its
human UI specification/layout gate remain separate.
