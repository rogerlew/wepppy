# Code Review Findings

**Reviewer Subagent**: `reviewer` (`019d26e7-a24b-7ba0-ad09-9f8f446b0dfb`)  
**Review Date**: 2026-03-25

## Findings and Disposition

1. **High**: New disturbed CSV download route could be unreachable behind Caddy `/download/*` browse proxy routing.
- Status: **Resolved**
- Fix:
  - Reverted editor CSV URL back to `download.download_with_subpath` (`disturbed/disturbed_land_soil_lookup.csv`) in [`wepppy/weppcloud/routes/nodb_api/disturbed_bp.py`](/workdir/wepppy/wepppy/weppcloud/routes/nodb_api/disturbed_bp.py).
  - Removed the custom `/download/disturbed_lookup_csv` route and corresponding stub declarations.
  - Restored route/template assertions in [`tests/weppcloud/routes/test_disturbed_bp.py`](/workdir/wepppy/tests/weppcloud/routes/test_disturbed_bp.py).

2. **Medium**: Merge-by-key save semantics retained stale rows when keys were edited/deleted.
- Status: **Resolved**
- Fix:
  - Reworked writer semantics to full-table replacement with hard validation in [`wepppy/nodb/mods/disturbed/disturbed.py`](/workdir/wepppy/wepppy/nodb/mods/disturbed/disturbed.py).
  - Added explicit rejection when payload is missing existing keyed rows (`rows payload is missing existing lookup rows; refresh and retry`).
  - Added duplicate-key rejection and tests.

3. **Medium**: Sparse dict-row payloads could blank unspecified columns.
- Status: **Resolved**
- Fix:
  - Added strict missing-column validation for mapping rows before write.
  - Added regression test coverage for sparse mapping rejection in [`tests/nodb/mods/test_disturbed_lookup_persistence.py`](/workdir/wepppy/tests/nodb/mods/test_disturbed_lookup_persistence.py).

## Residual Risks

- Explicit row deletion via partial-table submission is intentionally rejected by guardrails; users must submit a complete edited table.
- Full Caddy/proxy integration for this flow is not exercised in unit tests; route URL behavior remains aligned with existing browse-path conventions.

## Validation Evidence

- `wctl run-pytest tests/weppcloud/routes/test_disturbed_bp.py --maxfail=1`
- `wctl run-pytest tests/nodb/mods/test_disturbed_lookup_persistence.py --maxfail=1`
- `wctl run-pytest tests/nodb/mods -k disturbed --maxfail=1`
- `wctl run-stubtest wepppy.weppcloud.routes.nodb_api.disturbed_bp`

---

## Reopen Cycle: UI Safeguards (2026-03-26)

**Reviewer Subagent**: `reviewer` (`019d27ab-61ab-7a40-bc1b-ef19d96b706a`)  
**Review Date**: 2026-03-26

### Findings and Disposition

No new medium/high correctness defects were reported beyond implemented scope. The review confirmed that reopen-cycle goals are present in code:

- Strict `if_match_sha256` precondition handling for disturbed lookup writes.
- Atomic lookup snapshot load (`csv + hash`) for editor baseline consistency.
- In-flight save guardrails and stale lockout/recovery controls.
- Route-level optimistic-concurrency tests and full validation sweep.

### Reopen Residual Risks

- Stale polling and lockout UX is covered by route/template assertions, but not by browser E2E automation; regressions in polling timer behavior would be detected later than route regressions.

### Reopen Validation Evidence

- `wctl run-pytest tests/weppcloud/routes/test_disturbed_bp.py --maxfail=1`
- `wctl run-pytest tests/nodb/mods/test_disturbed_lookup_persistence.py --maxfail=1`
- `wctl run-pytest tests/nodb/mods -k disturbed --maxfail=1`
- `wctl run-stubtest wepppy.weppcloud.routes.nodb_api.disturbed_bp`
- `wctl check-test-stubs`
- `wctl run-pytest tests --maxfail=1`
