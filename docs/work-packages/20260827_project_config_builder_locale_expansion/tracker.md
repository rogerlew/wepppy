# Tracker - Project Config Builder Locale Expansion (WP12C)

## Quick Status

**Timezone**: UTC
**Started**: 2026-08-27 15:40 UTC
**Current phase**: Standalone contract checkpoint commit
**Last updated**: 2026-08-27 18:05 UTC
**Next milestone**: standalone checkpoint commit
**Security impact**: `high`
**Dedicated security review**: `yes`
**Security artifact**: `artifacts/20260827_security_review.md`
**Parameterization ADR**: `docs/adrs/ADR-0047-project-config-locale-authority.md`
**Initiative / canonical branch**: `feature/project-owned-config` / `master`
**Promotion policy**: WP12C pushes the initiative branch only; WP12 owns merge
and production

## Task Board

### In Progress

- [ ] Commit the standalone contract checkpoint.

### Pending

- [ ] Commit the standalone contract checkpoint before implementation.
- [ ] Implement typed climate authority and complete Europe/Canada/Australia/
  Earth profile data.
- [ ] Generate locale/data components and a validated graph per profile.
- [ ] Update Builder API/UI selection and validation to use the selected graph.
- [ ] Add direct backend/frontend compatibility and hostile-state tests.
- [ ] Pass local gates and independent implementation/security reviews.
- [ ] Deploy without rebuilding to exact host `forest` and prove all advertised
  providers plus one created/reopened run per newly exposed profile.
- [ ] Close WP12C and hand the accepted revision to WP12.

### Blocked

None.

### Done

- [x] Operator approved the exact exposed locale set and Canada provider policy.
- [x] Confirmed WP12B is closed and created this successor package.
- [x] Verified local/origin initiative revision `e1ef3b8df`, canonical origin
  `6af9ecdd6`, and that canonical is an ancestor of the initiative branch.
- [x] Made Vanilla CLIGEN the explicit climate-mode default for all five
  profiles.
- [x] Operator explicitly ratified amendment `PC-23/WP12C-20260827-1` and
  authorized the standalone checkpoint commit and subsequent implementation.
- [x] Correctness and security contract re-reviews are Ready with no unresolved
  blocking or high/medium findings.
- [x] Governance contract re-review is Ready with no remaining blockers; both
  independent contract reviews are complete.

## Decisions Log

### 2026-08-27 15:40 UTC: Canada is distinct and globally sourced

**Decision**: Add stable profile `canada` with runtime token `canada`.
Its only DEM is Copernicus 30 m, only soil dataset is ISRIC global, land-cover
datasets are C3S 1992-2020, and it offers Vanilla CLIGEN plus observed Daymet,
defaulting to Vanilla CLIGEN with GHCN stations.

**Rationale**: Canada-wide coverage must not be represented as British Columbia
or as the Global Earth locale, and the operator explicitly chose global data
providers plus Daymet observed climate.

### 2026-08-27 15:40 UTC: Locale profiles own dataset availability

**Decision**: A selected profile's typed DEM, soil, landuse, and climate source
IDs are the sole authority for Builder options and validation.

**Rationale**: A second global support flag or frontend list would recreate the
drift that WP12B removed from run views.

### 2026-08-27 16:02 UTC: Interpret the operator's integration instruction

**Decision**: The operator's sequence—integrate the other locales, limit the
set, then explicitly restore Canada with global datasets and observed Daymet—is
approval of the complete user-visible five-profile behavior. Existing canonical
EU/AU/Earth runtime providers supply their dataset/default details. The
locale-keyed response is an additive internal API mechanism for implementing
that approved dependent-control behavior, not a new user option.

**Rationale**: The implementation does not invent new scientific providers;
it exposes the existing locale-specialized paths and makes the profile the
authority the operator requested.

### 2026-08-27: Vanilla CLIGEN and station-database authority

**Decision**: Every exposed locale offers Vanilla CLIGEN. Add Climate Station
Database as a separate profile-owned axis. Continental US exposes Legacy, 2015,
and GHCN and defaults to 2015; Europe, Canada, Australia, and Earth expose only
GHCN. Vanilla CLIGEN is the climate-mode default for every locale; regional
observed modes require explicit selection.

**Rationale**: Climate generation mode and the station-statistics catalog are
different choices and must not be conflated or inferred from one another.

## Risks and Issues

| Risk | Severity | Mitigation | Status |
| --- | --- | --- | --- |
| Provider exists in code but is absent on Forest | High | Presence/health and real execution gate every advertised provider | Open |
| New graph reader breaks stored Continental-US v2 configs | High | Immutable profile contracts and historical round-trip fixtures | Open |
| UI and server select different locale graphs | High | One description payload plus paired frontend/API rejection tests | Open |
| Canada runtime token falls through US-specific behavior | High | Direct generated-config and created-run execution evidence | Open |
| Concurrent CLIGEN requests mix database rows and PAR roots | High | Instance-local resolver state plus direct real concurrent Legacy/2015/GHCN isolation test | Open |
| Old Builder client cannot express schema-v3 station DB | Medium | Version description/requests; retain v2 response shape for parsing and fail old creation explicitly | Open |

## Verification Checklist

- [ ] Focused Python tests pass.
- [ ] Full Python suite passes.
- [ ] Frontend lint and tests pass.
- [ ] Stub/API gates pass.
- [ ] Docs lint passes.
- [ ] Correctness, governance, and security findings are dispositioned.
- [ ] Exact-host `forest` acceptance is recorded.
