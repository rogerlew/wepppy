# Table Overflow Discoverability Contract Decision

**Decision ID**: `A11Y-TABLE-20260829-1`
**Recorded**: 2026-08-29 01:25 UTC
**Starting implementation revision**: `75eb240c8dbffea6beb639c9707821d3d877ac2d`
**Status**: Operator-authorized; implementation pending

## Authority

The operator directed: “scaffold and execute work-package to add this
accessibility feature. don't ask me to ratify a contract. this is the
authority.” This is explicit approval of the exact bounded behavior discussed:
one shared enhancement for `.wc-table-wrapper`, activated only when columns
overflow, with discoverability instructions and keyboard access.

At 2026-08-29 01:38 UTC the operator added: “please also modify the slope
values in the Hilllope summary and Channel summary tables on the
report/wepp/summary page to 3 decimal places.” This directly authorizes the
display-precision delta below without another ratification step.

## Applicable Current Contract

- `docs/ui-docs/contracts/table-overflow-discoverability-contract.md` owns the
  exact shared overflow and WEPP slope-display behavior. Implementation
  conformance is pending.
- `docs/standards/contract-first-change-standard.md` governs sequencing and
  review of intended shared UI behavior changes.

The style and accessibility guides are synchronized guidance, not normative
authority under the finite contract-first set.

No route, API, RQ, NoDb, persistence, data-schema, scientific parameterization,
or deployment contract applies.

## Exact Normative Delta

For each `.wc-table-wrapper`, the Pure UI must determine whether horizontal
content overflows its visible box. While overflow exists, the UI must:

1. display concise instructions that additional columns are available and can
   be reached through horizontal scrolling, Shift plus mouse wheel, or keyboard
   focus followed by Left/Right Arrow;
2. make the scroll container sequentially keyboard focusable only when no
   authored focus policy exists;
3. expose a named or described region without replacing authored accessible
   semantics;
4. display an obvious focus indicator; and
5. re-evaluate after relevant layout changes and dynamic wrapper insertion.

When overflow does not exist, the UI must not add a hint or keyboard stop and
must remove only semantics it generated during an earlier overflowing state.
Repeated enhancement must be idempotent. Eligibility and accessible-name,
attribute-precedence, description-token ownership, hidden/malformed behavior,
and input semantics are defined exactly by the canonical contract.

In `reports/wepp/summary.htm`, numeric values under the exact `Slope` header in
the Hillslope Summary and Channel Summary HTML tables must display with exactly
three digits after the decimal point. Missing values retain the existing em
dash. Raw numeric sorting keys, report data, stored/model values, other columns,
and CSV output remain unchanged.

## Rationale and Rejected Alternatives

Native `overflow-x: auto` is insufficient because operating systems may hide
scrollbars and users cannot infer Shift-wheel or keyboard navigation. Static
instructions on every table were rejected because they create noise and imply
overflow where none exists. Per-template changes were rejected because the
shared wrapper is already the established behavior seam. Forced always-visible
custom scrollbars and intercepted arrow-key handlers were rejected initially
because they add layout and input regression risk; native focused scrolling is
preferred when rendered evidence confirms it.

## Compatibility and State Matrix

- Wrapper absent: no-op.
- Wrapper fits: no generated UI, semantics, or tab stop.
- Wrapper overflows: generated hint and accessible focus behavior.
- Overflow starts or stops after resize/zoom: state synchronizes.
- Wrapper inserted dynamically: it is registered and synchronized.
- Authored focus/ARIA attributes: preserved and composed with generated
  description where safe.
- Wrapper without a table or malformed descendants: measurement-based no-op;
  no exception reaches the user.

The overflow feature changes no table values, widths, wrapping, sorting,
downloads, links, or form behavior. The slope delta changes HTML text formatting
only; it does not round or mutate the scientific value and is not a
model/workflow parameterization change requiring an ADR.

## Security and Data Impact

Security impact is `none`. The module reads DOM geometry and adds local
presentation attributes. It accepts no HTML, makes no requests, persists no
state, and crosses no trust boundary. Data/schema impact is none.

## Regression Evidence

- Deterministic Jest coverage for every state above, idempotence, and attribute
  ownership.
- Template and CSS contract assertions for the shared load and focus styling.
- Direct template rendering for numeric, zero, and missing slopes in both
  requested tables, a non-slope ratio value, raw sort keys, and CSV wiring.
- Rendered-browser evidence for visible hint, Tab reachability, Right Arrow and
  Shift-wheel movement, AA-theme focus styling, and no document-level
  horizontal overflow.
- Focused axe scan and 200-percent zoom/narrow viewport observation.
- Frontend lint/full Jest and documentation lint.

## Scope Boundary

The checkpoint allowlist is:

- `PROJECT_TRACKER.md` (only the new package entry and tracker header counts);
- `docs/ui-docs/accessiblity.md` (only section 8; its preexisting project-config
  update hunk is excluded);
- `docs/ui-docs/ui-style-guide.md` (only Pattern #5 guidance);
- `docs/ui-docs/contracts/table-overflow-discoverability-contract.md`; and
- every file under
  `docs/work-packages/20260828_table_overflow_discoverability/`.

The implementation allowlist is:

- `wepppy/weppcloud/static/js/table_overflow_accessibility.js`;
- `wepppy/weppcloud/templates/base_pure.htm`;
- `wepppy/weppcloud/static/css/ui-foundation.css`;
- `wepppy/weppcloud/templates/reports/wepp/summary.htm`;
- `wepppy/weppcloud/controllers_js/__tests__/table_overflow_accessibility.test.js`;
- `tests/weppcloud/routes/test_pure_controls_render.py`;
- `tests/weppcloud/test_ui_foundation_css.py`; and
- `wepppy/weppcloud/static-src/tests/smoke/table-overflow-accessibility.spec.js`.

The final review artifact is
`artifacts/20260829_implementation_correctness_review.md`. Any newly discovered
required path stops implementation and requires checkpoint amendment/review.
Deployment, push, merge, production, table layout, report/CSV data, and
unrelated accessibility remediation are excluded.

## Dirty-Worktree and Checkpoint Controls

At the starting revision, every modified path outside the checkpoint allowlist
is preexisting and excluded. The exact excluded paths are:

- `code-quality-report.json` and `code-quality-summary.md`;
- `docker/validate-cap-runtime-contract.sh`;
- `docs/infrastructure/incident-2026-08-25-production-compose-partial-build.md`;
- `docs/standards/hardening-lifecycle-standard.md`;
- `docs/ui-docs/cap-js-captcha-auth.md`;
- `docs/work-packages/20260819_eu_disturbed_soil_hardening/package.md`, its
  active ExecPlan, and its tracker;
- the rollout runbook, active ExecPlan, and tracker under
  `docs/work-packages/20260823_session_cookie_namespace_migration/`;
- the package, active ExecPlan, and tracker under
  `docs/work-packages/20260825_cap_runtime_deploy_hardening/`;
- `services/cap/canary.js`;
- `tests/eu/soils/test_esdac_build.py` and
  `tests/eu/soils/test_esdac_soil_build.py`;
- `wepppy/eu/soils/esdac/readme.md` and `wepppy/eu/soils/soil_build.py`;
- `wepppy/weppcloud/controllers_js/__tests__/control_base.test.js`; and
- `wepppy/weppcloud/templates/locations/portland/index.htm`.

`PROJECT_TRACKER.md` contains a preexisting ESDAC package hunk and
`docs/ui-docs/accessiblity.md` contains a preexisting section 7 project-config
hunk; both are excluded and require hunk-aware staging. Before commit, compare `git diff --cached
--name-only` and `git diff --cached` against the exact allowlist and confirm no
unrelated hunk is staged.

Record the full standalone checkpoint SHA in `tracker.md` and verify with
`git merge-base --is-ancestor <checkpoint-sha> HEAD` immediately before the
first implementation or test edit.
