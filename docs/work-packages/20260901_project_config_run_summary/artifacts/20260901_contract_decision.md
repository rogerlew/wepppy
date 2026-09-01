# Contract Decision - Project Config Run Summary

**Status**: Approved and independently reviewed; checkpoint commit pending

**Date**: 2026-09-01
**Starting implementation revision**: `9a34b336fc901cb31341a3f680e8fef0a8903b29`

## Requested Outcome

On Config Builder run pages, show the effective locale beside the projection
and provide More -> Config Summary with Locale, Delineation Backend,
Representation, DEM Data Source, Cell Size (m), and CLIGEN Database.

## Applicable Canonical Contracts

- `docs/schemas/project-owned-config-contract.md`
- `docs/ui-docs/controller-contract.md` for project-config run authority; the
  new generic dialog requirements are owned directly by canonical section 7.8
- `docs/schemas/project-owned-config-contract.md`, section 7.8, Config Builder
  run summary
- `docs/standards/contract-first-change-standard.md` (process authority)

`docs/ui-docs/accessiblity.md` routes modal/focus implementation toward the
controller and style guidance, but neither is treated as a pre-existing generic
modal contract. Canonical section 7.8 directly owns the new dialog behavior.

## Proposed Normative Delta

The Config Builder run page exposes a read-only effective-configuration summary.
When summary context is available, the header places a locale pill immediately
after the projection pill. The More menu exposes a Config Summary dialog with
the six requested rows in the requested order. The summary reads effective run
values, does not mutate state, and does not replace absent values with current
registry defaults.

Representation displays exactly `Single OFE` or `Multiple OFE`. Locale, DEM
Data Source, CLIGEN Database, and normalized backend render the canonical IDs
specified by section 7.8 without a display-name substitution. Cell size
displays the effective resolution in meters.

## Discrepancy Classification

This is an additive intended-behavior change that fills a canonical contract
gap. It is not a conformance fix, urgent restoration, migration, or incident
mitigation. Implementation conformance is pending and no production
implementation file has been edited at this checkpoint.

## Operator-Confirmed Display Decision

The pill uses the run's effective canonical locale ID. For the canonical
Continental US locale, it reads `locale: continental-us`. The request's
`us-contintental` example is not introduced as an alias. The operator confirmed
this decision on 2026-09-01 at 18:07 UTC.

## Unavailable-Value Decision

An unavailable field displays `Not available`; the row and modal remain
present. This is the smallest stable behavior that keeps the requested table
shape visible without inventing a current-registry default. The operator
explicitly approved the complete edge policy on 2026-09-01: `/config/` pages,
including nested/PUP runs, always show the six-row modal; the locale pill is
omitted only when locale is unavailable; and other config stems omit all
summary UI.

## Compatibility and Data Impact

The change is additive and read-only. It adds no stored key, column, manifest
field, API, RQ edge, or model parameter. Existing runs and links remain
unchanged. Shared-header reach must be explicitly gated so non-Config-Builder
pages do not imply Config Builder authority.

## Security Impact

Triage is `low` because this adds a new HTML disclosure/rendering sink. The
values are already loaded behind existing project-read authorization in
sections 12 and 13, and the change adds no endpoint, mutation, input, or new
audience. Evidence must prove authorization denial precedes rendering and Jinja
escapes hostile values. Re-triage if implementation requires a new API or
broader exposure.

## State and Error Matrix

### Input and request matrix

| Input/request | Proposed behavior | Required evidence |
| --- | --- | --- |
| Route config stem is `config` | Modal and six rows render; locale pill renders when locale resolves | Direct route/template test |
| Route config stem is not `config` | Pill, launcher, and modal are absent | Direct rendering test |
| Project-read authorization denied | Existing denial occurs before summary rendering | Route authorization test |
| Nested/PUP route with active stem `config` | Summary uses active resolved context | Direct nested/PUP test |
| `playwright_load_all` on another stem | Summary remains absent | Direct rendering test |

### Runtime state matrix

| State | Proposed behavior | Required evidence |
| --- | --- | --- |
| Required value never persisted / absent | Row displays `Not available`; missing locale also omits pill | Direct route/helper test |
| Required value present but empty | Row displays `Not available`; page remains usable | Direct rendering test |
| Populated stored Builder authority | Pill and all six effective values render | Direct route/template test |
| Supported legacy/live authority | Locale and runtime-backed rows render; stored-selection rows remain unavailable | Route/helper test |
| Malformed or hostile display value | Value is escaped and page remains bounded | Direct rendering test |

### Per-field authority

| Field | Authority and precedence |
| --- | --- |
| Locale | Non-empty canonical profile ID resolved from effective run config |
| Delineation Backend | Normalized effective runtime backend ID |
| Representation | Effective runtime model (`Single OFE` or `Multiple OFE`) |
| DEM Data Source | Persisted stored-capability selected canonical ID only |
| Cell Size (m) | Effective runtime numeric cell size |
| CLIGEN Database | Persisted stored-capability selected canonical ID only |

Live legacy or preset graph defaults never fill DEM Data Source or CLIGEN
Database. Missing required persisted/runtime evidence yields `Not available`.

No new user-reachable exception is intended. Failure to resolve an optional
display value must follow the approved unavailable policy, not cause a 500.
Unexpected failures at existing run-load boundaries retain their current
contracts; this feature must not add broad exception handling.

## Proposed Regression Evidence

- Focused Jinja/route tests for exact pill position and six-row table.
- Single- and Multiple-OFE formatting tests.
- Absent, empty, populated, supported legacy, and hostile-display tests.
- Modal accessibility semantics plus authenticated Config Builder axe/reflow
  smoke with the modal open when needed.
- Existing full frontend and Python handoff gates.

## Approval and Review Register

- **Operator approval**: Canonical locale-ID display approved 2026-09-01 18:07
  UTC; execution authorized 2026-09-01 18:09 UTC; complete corrected edge-policy
  matrix explicitly approved 2026-09-01
- **Independent review 1**: Renewed correctness review Ready; see
  `20260901_contract_correctness_review.md`
- **Independent review 2**: Renewed governance review Ready; see
  `20260901_contract_governance_review.md`
- **Finding disposition**: All medium/high findings resolved; both renewed
  reviews Ready
- **Canonical contract amendment**:
  `docs/schemas/project-owned-config-contract.md`, section 7.8, prepared
- **Standalone ancestor revision**: Pending

Implementation files must not be edited until every pending checkpoint item is
complete and the ancestor revision is recorded in the tracker.
