# Runtime findings and disposition

Status: medium/high findings resolved; final broad gates passed. Reviews/evidence dates are UTC, 2026-09-16.
Reviewed ancestor: `ac4deb681`. Implementation commit pending.

## Resolved backend findings

COR-R01 (medium): saved timestamps prevented hash-identical archive restores
from downloading. Compare accepted size/hash; retain before/after descriptor
stat checks for mutation during read. Actual copied/restored files and injected
in-read mutation tests pass. Independent correctness and security confirmed.

COR-R02 (medium): valid M3 terrain unavailability could lose its specific reason
despite 100% common soil/SBS support. Preserve accepted safe reason codes and
explain terrain truncation/area mismatch separately from input coverage. Actual
validated partial-M3 fixtures and frontend regression pass; reviewers confirmed.

SEC-R02 (low): symlinked redisprep.dump could enter existing currentness reads.
Skip symlink/nonregular dumps, preserving values with unknown currentness.
Actual symlink fixture proves no get_state call or target write.

## Frontend findings

COR-R03 (medium, resolved): current-page membership incorrectly cleared an
eligible off-page selection when changing duration. Preserve selection using
its saved three-duration rows and actual filters, with generation-safe bounded
detail reads when needed. Three regressions and the rebuilt M1 browser prove
selection survives duration reset and expands again on returning to its page.
Independent correctness and security confirmed conformance.

SEC-R01 (medium): Unitizer rerender re-enabled event buttons during a pending
query. Persistent loadingQuery and guarded detail loading retain query authority;
regression exercises a unit change while the request is pending. Security review
confirmed resolution.

LIVE-01: browser found nonexistent public Unitizer.getPrecision use, hidden by
the mock. Use public category-unit precision and a real UnitizerClient regression.
Corrected browser run reaches detail/paging/units/CSV with no page errors.

UX-F01 (medium, resolved): failed first/last-row event detail and paging recovery
must remain locally discoverable, not only above the summary. Keep inline error
and Retry with stable focus; no modal or automatic scroll jump.

UX-F02 (medium, resolved): CSV probabilities are fractions but were unlabeled
while UI is percent. Explicit fraction headers/context/help must retain exact
numbers and prevent a 100-fold interpretation error. No scientific formula change.

UX-F03 (low, optional deferred): consider normal text for filter/export guidance,
not low-emphasis muted styling in dark themes; no shared-theme redesign.
The dedicated UX reviewer approved the final report with this optional polish
remaining; no medium/high UX findings remain. Verified screenshots and CSV are
in browser_m1_verified, with independent review of local recovery controls.

## Passive Unitizer bootstrap conformance fix

LIVE-02: `_base_report.htm` calls Project.unitChangeEvent on DOMContentLoaded,
which posts set_unit_preferences even on passive view. The failed browser record
is retained under browser_m1_final. This violates the already accepted passive
no-project-write report contract; independent correctness explicitly classified
the bounded correction as conformance, not new intended behavior. Security
approved the same boundary before edits.

Wrap only the initial trigger invocation in `report_unitizer_bootstrap`; default
retains all existing report behavior. Override only in the new postfire template.
Synchronize the ready client from DOM preferences and render without persistence,
including when the client already exists. Preserve shared Project initialization
and explicit modal actions. Add default-versus-postfire rendered-template and
existing-English client regressions. Final browser proof must show no preference
POST and unchanged project state.

The existing exact `/runs/<runid>/<config>/recorder/events` observability POST
is distinguished from model/project mutations. Do not allowlist other POSTs or
claim zero session/observability effects. Explicit shared preference-save actions
remain separately authorized presentation changes, not passive report reads.

Final browser_m1_verified and browser_m3_verified both pass: zero unexpected
mutating requests, zero page errors, unchanged 18/23 protected root files, exact
fixed and ordinary artifact downloads. Broader saved-bundle checks additionally
include accepted-attempt files (23/28 unchanged). Live M3 uses its actual
disturbed9002_wbt configuration; an initial harness attempt using config failed
ordinary browsing and was corrected without changing production routes.
