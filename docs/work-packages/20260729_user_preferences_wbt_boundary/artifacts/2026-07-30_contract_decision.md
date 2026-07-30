# SURF-14A Contract Decision

**Status**: Draft; operator decision recorded, independent reviews and
standalone ancestor pending

**Starting implementation revision**:
`715417f7081ea12e168e10426603445ec5140520`

**Decision venue**: Codex API workspace thread, 2026-07-29 21:10 PDT
(2026-07-30 04:10 UTC)

**Participants present**: requesting WEPPcloud operator; Codex

**Stakeholder input relayed**: Mariana requested an actionable error that tells
the user to select another outlet or change the extent rather than silently
accepting a clipped watershed. Mariana was not present in this decision venue.

## Applicable Authority

- `docs/standards/contract-first-change-standard.md`;
- `docs/standards/parameterization-adr-standard.md`;
- `docs/schemas/weppcloud-csrf-contract.md`;
- `docs/schemas/rq-response-contract.md`;
- `docs/schemas/nodb-persistence-concurrency-contract.md`;
- SURF-14 Profile/Session concise intent contract;
- SHR-05 Unitizer Preferences concise intent contract;
- DOM-05A Channel Delineation/Topaz contract;
- the Pure UI child package register's new SURF-14A entry; and
- this package's `package.md` Normative Contract, pending ratification by the
  required checkpoint process.

No existing contract authorizes account preference mutation, creation-time
account defaults, or configurable WBT edge behavior. This is an intended
behavior change, not a conformance fix.

## Exact Normative Delta

1. Add one typed account preference row per User with exact values
   `config|si|english` and `config|warn|error`.
2. Add login/CSRF-protected `/preferences` GET/POST routes and a Profile link,
   using the existing PureCSS account shell and form macros.
3. Use the exact boundary label `Stop with an error`.
4. Resolve new-project values using explicit project input, then account
   preference, then project config, and snapshot the result into run state.
5. Preserve existing runs, shared runs, anonymous creation, and source values
   on forks.
6. Add `[watershed.wbt] boundary_touch_behavior = "warn"` with exact
   `warn|error` validation.
7. For WBT edge contact, warn and continue or raise the existing typed edge
   exception with an actionable message and no consumable stale success state.

## Rationale and Rejected Alternatives

Typed PostgreSQL columns were selected because the values are small,
account-scoped, security-sensitive enums. Cookies and local storage cannot
serve RQ workers or multiple browsers. Run NoDb state has the wrong lifetime.
A JSON blob or generic key/value table weakens database validation and makes
contract evolution less visible.

Live profile resolution during every view/job was rejected because it would
make shared and historical runs depend on the current viewer and mutable
account state. Snapshotting during project creation preserves reproducibility.

`Warn` as the account default was rejected because it would override a config
set to `error` for every existing user. Account default `config` plus config
default `warn` preserves existing behavior while keeping both layers useful.

`Crash` was rejected as a label. `Stop with an error` accurately describes a
controlled typed job failure.

## Compatibility

The database migration is additive. Existing users have no required row and
resolve to `config`/`config`. Existing projects and persisted Unitizer maps are
unchanged. Forks retain source state. Anonymous projects use config. WBT keeps
its current warning behavior unless a config or account preference explicitly
selects `error`. TOPAZ is unchanged.

## Security and Operations Impact

Security impact is high because the feature adds authenticated database
mutation, CSRF-sensitive form handling, account-to-run propagation, and an RQ
failure policy. Exact allowlists, atomic transactions, DB constraints,
failure-atomic project creation, escaped rendering, no secret logging, typed
errors, and no silent fallback are mandatory.

The operator authorizes the reviewed additive migration on Forest after the
contract ancestor, implementation, local migration/full-suite validation, and
final reviews pass. This does not authorize production/wepp1 migration.

## Regression Evidence Required

- model constraints, cascade, atomic save, and migration
  upgrade/downgrade/upgrade;
- actual preference-page/Profile rendering and prefix-aware navigation;
- login, CSRF, exact enum, hostile input, PRG, and no-partial-write routes;
- complete precedence, explicit input, anonymous, identity failure, existing,
  shared, and fork creation matrices;
- persisted Unitizer and Watershed snapshot evidence;
- synthetic WBT no-edge/all-edge/corner/nodata, warn/error, deterministic IDs,
  actionable message, stale-readiness, and rerun recovery;
- canonical rq-engine error-envelope evidence;
- full Python/frontend/docs/stub/graph gates as applicable;
- local E2E and Forest migration/canary artifacts.

## Operator Approval

The requesting operator explicitly approved `Stop with an error`, requested
the work-package scaffold, and granted authority to run the package's reviewed
database migration on Forest. Approval does not waive contract-first reviews,
the standalone ancestor, tests, or final review gates.

## Checkpoint Gate

- [x] Starting revision and normative delta recorded.
- [x] Operator decision and scoped Forest authority recorded.
- [x] Applicable contracts, rationale, compatibility, security, and regression
  plan recorded.
- [ ] Independent governance/correctness review passed.
- [ ] Independent operations/security review passed.
- [ ] Findings disposition complete.
- [ ] Documentation-only standalone ancestor committed and recorded.
