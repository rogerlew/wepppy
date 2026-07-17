# Post-Fix Review B — Corrected 67-Unit Register / Coverage Ledger

Closure-ready: **NO.**

## High

### PF-H1 — Pure-base/template population is incomplete

The claimed complete Pure-base/template population omits concrete stateful or
privileged Pure surfaces from the coverage ledger and an explicit package/parent
decision:

- `routes/rq/info_details/templates/info_details.htm` extends `base_pure.htm`
  and exposes Admin/Root-only Redis/RQ job/submitter state via
  `routes/rq/info_details/routes.py:147-201`.
- `templates/reports/deval_loading.htm` extends `base_pure.htm` and implements RQ
  job polling/terminal/error behavior, enqueued and rendered from
  `routes/weppcloudr.py`.
- `templates/reports/ermit_export_download.htm` extends `base_pure.htm`, obtains
  a session token, submits/polls an export, and downloads a blob behind the
  auth+CAP route in `nodb_api/wepp_bp.py`.

These are not passive report shells. Add explicit ledger rows and assign each to
an exact existing owner or create additional bounded surfaces; record
route/tests/security, update the count when split, and itemize direct report-base
consumers/parents sufficiently to prove the checked transitive-template claim.

### PF-H2 — `inventoried` violates mandatory metadata

The coverage ledger labels items `inventoried` while its mandatory metadata
requires canonical contract path, child-package path, manifest key/globs/tests,
status, last verified commit/date, gates/endpoints, and security. Add the
item-level metadata or keep incomplete rows `candidate` and redefine the exact
promotion point. Do not freeze a coverage authority whose states contradict its
schema.

### PF-H3 — GOV-99 dependency is self-referential and non-finite

GOV-99 depends on “All registered packages”; GOV-99 is itself registered. A
literal executor produces a self-cycle, and the phrase is not a finite edge set.
Replace it with all other units plus explicit finite groups/IDs, or a defined
expansion syntax that excludes GOV-99, and verify the graph is acyclic.

## Medium

### PF-M1 — Dependencies are not machine-executable

The global inherited-spine rule is sound human ordering, and DOM-01 now
explicitly depends on its foundations, but undefined range tokens remain. The
Batch external prerequisite names the package path but not its accepted
completion state/revision. Define exact range expansion or expand the IDs;
require the external package to be closed at a named revision; record and
validate the resulting DAG.

### PF-M2 — Geneva route ownership overlaps

DOM-27 claims the whole Geneva route family while SURF-11 claims the interactive
summary query/map/unitizer contract whose endpoints live in the same file. Name
the route functions/endpoints owned by DOM-27 versus SURF-11 and make one the
producer owner for each.

### PF-M3 — Initial Review B severity count is inaccurate

The tracker says two high, five medium, and two low findings. The verbatim
initial review contained two high, six medium, and two low findings: M1 pilot
sequencing, M2 finite dependencies/console utility, M3 security, M4 broad
boundaries, M5 schedule, and M6 acceptance.

## Low

### PF-L1 — Formatting and canonical lint

Wrap the overlong boundary-rule sentence. Canonical doc lint could not be rerun
by the reviewer because bare `wctl` failed while importing missing `typer`;
obtain a fresh canonical lint result before closeout.

## Prior Findings — Concise Raw Restatement

- Initial H1: the coverage authority was only historical waves/checklist while
  allocations lived in the child register; populate it or collapse authority.
- Initial H2: `selection_utils.js` and Unitizer producer/route ownership were
  absent/duplicated.
- Initial M1: WATAR preceded its foundations without re-verification.
- Initial M2: Batch/report/console dependencies were prose/non-finite and
  `console_utils.js` lacked a shared producer edge.
- Initial M3: Unitizer and Geneva report security tiers contradicted
  auth/CAP/query boundaries.
- Initial M4: known multi-owner/global-fan-out packages were called stable
  without boundary probes/estimates.
- Initial M5: 12-month/7-month lower schedules contradicted package
  arithmetic/capacity.
- Initial M6: universal controller evidence made governance packages uncloseable
  and residual-risk wording needed separation from unresolved findings.
- Initial L1: the 33-entry/33-package statement hid a many-to-many mapping.
- Initial L2: GOV-00 needed explicit mapping to the existing umbrella and the
  count needed to distinguish 67 total units from 66 future directories.

## Post-Fix Disposition Verification

Resolved: producer ownership for `selection_utils.js`, `console_utils.js`, and
Unitizer; Project is a Unitizer consumer. Resolved: foundations precede final
WATAR verification and DOM-01 explicitly depends on them. Resolved: Unitizer and
Geneva security forecasts are high when their auth/query boundary changes.
Resolved: broad Map/Landuse/Climate/AgFields/WEPP/shared/Batch scopes were
pre-split and every ID has a default/exception estimate plus first-day split
probe. Resolved: serial/parallel schedules are materially credible at 24-36 and
12-20 months. Resolved: acceptance is where-applicable with dual-reviewed N/A,
governance substitutions, and residual risk is not relabeled a resolved finding.
Resolved: GOV-00 maps to the existing umbrella, future directories are distinct,
and the 33 bootstrap keys have clear primary/facet ownership. Resolved: derived
README index versus audit/execution/manifest/domain authority is separated.
Resolved: operator-authorized dispatch remains bounded/logged and dual review is
independent with post-fix confirmation.

Final decision: **NOT closure-ready** because PF-H1 through PF-H3 remain. No
files were edited.
