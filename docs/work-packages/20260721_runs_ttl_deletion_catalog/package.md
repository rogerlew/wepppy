# Runs TTL Deletion Catalog

**Stable ID**: REM-02  
**Status**: Complete; implementation committed after contract ancestor `d3380287ca706360879240c3d203c5e7cc2be9ef`
**Timezone**: UTC

## Overview

The authenticated Runs catalog currently displays a run's database `last_modified`
timestamp. Users cannot see when a run with active time-to-live (TTL) cleanup is
scheduled for deletion, and the existing TTL policy explanation is embedded in a
general user guide. This bounded remediation makes the active deletion timestamp
visible, preserves the last-modified timestamp for runs whose TTL deletion is
disabled, and publishes one dedicated Usersum page that explains the distinction.

## Scope

### Included

- Read-only TTL metadata for each catalog row: `expires_at` and whether deletion
  is active.
- The Runs catalog JSON payload, table column, and client-side row rendering.
- A dedicated end-user Usersum TTL-deletion guide and its manifest/catalog entry.
- Focused route/template/Usersum regressions, contract evidence, security review,
  and two independent reviews.

### Explicitly Out of Scope

- TTL duration, expiry calculation, access-touch behavior, GC scheduling, deletion
  execution, and the existing Disable TTL Deletion permission/mutation endpoint.
- Runs catalog ownership, map, delete, polling, sorting, auth, CSRF, RQ, or
  database-schema behavior beyond carrying read-only TTL presentation metadata.
- Production deployment or changes to existing run metadata files.

## Success Criteria

- Active rolling TTL rows show `TTL Deletion: <time>` and a `Learn More` link to
  the dedicated Usersum document.
- Rows whose policy has TTL deletion disabled show `Last Modified: <time>` in
  the same column instead of an expiry date.
- The catalog preserves its existing `last_modified` key and adds a read-only
  `ttl_deletion_at` field to every returned row; it is `null` for fallback states.
- The Usersum document states that activity refreshes a rolling TTL, explains why
  an expiry may be absent, and describes the existing role-gated disable control.
- Focused tests, documentation lint, frontend lint/tests, broad-exception check,
  and final independent reviews pass with no unresolved high/medium findings.

## Security Impact and Review Gate

- **Security impact triage**: `high`
- **Dedicated security review required**: yes
- **Rationale**: REM-02 borrows the registered high-security SURF-06 surface,
  which is an authenticated catalog exposing run-scoped metadata. The change must
  not bypass its existing owner filtering or disclose TTL metadata for runs the
  caller cannot already enumerate.
- **Security artifact**:
  `artifacts/2026-07-21_security_review.md`

## References

- `docs/standards/contract-first-change-standard.md`
- `docs/work-packages/20260716_pure_ui_contract_standardization_c/artifacts/child_package_register.md`
- `docs/ui-docs/contracts/runs-catalog-ttl-deletion-contract.md`
- `wepppy/weppcloud/utils/run_ttl.py`
- `wepppy/weppcloud/routes/user.py`
- `wepppy/weppcloud/templates/user/runs2.html`

## Documentation Impact

- **User documentation**: add the dedicated TTL deletion guide.
- **Developer documentation**: add the lifecycle-column contract, package plan,
  review evidence, and source/test matrix.
- **Operator documentation**: unchanged because TTL policy, the existing
  role-gated control, and deletion operations are untouched.
