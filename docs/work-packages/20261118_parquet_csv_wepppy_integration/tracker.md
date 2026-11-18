# Parquet CSV integration tracker

**Started / updated**: 2026-11-18 UTC
**Phase**: Scaffold complete; M0 pending
**Branch**: `codex/parquet-csv-cli-package`
**Security impact**: high; dedicated reviews required, not yet performed
**Plan**: [implementation_execplan.md](prompts/active/implementation_execplan.md)

## Progress

- [x] Inspect accepted standalone evaluation and current download branches/contracts.
- [x] Scaffold package, draft durable contract, checkpoint and active ExecPlan.
- [x] Record immediate cutover, no environment-facing configuration and no Python fallback.
- [ ] M0: Resolve compatibility, filter/environment contract changes, fixed settings and HTTP errors.
- [ ] M0: Independent contract reviews and checkpoint ancestor commit.
- [ ] M1: Promote/package native CLI and harness; close required compatibility gaps.
- [ ] M2: Wire all covered CSV routes, response ownership and shared admission; remove old path.
- [ ] M3: Exact-image workflow/resource/security validation; broad tests after wiring.
- [ ] M4: Final reviews, documentation, release/rollback handoff and evidence-based closeout.

## Decisions and rationale

2026-11-18, operator: immediate native cutover, no environment-variable-facing
configuration and no Python fallback. A single release path avoids retaining the
old resource-heavy implementation as a hidden failure mode. Exact wording is in
[integration contract: Authority and cutover policy](../../schemas/parquet-csv-integration-contract.md#authority-and-cutover-policy)
and [Configuration ownership](../../schemas/parquet-csv-integration-contract.md#configuration-ownership).

Prior operator decision retained: broad repository tests wait until integration
is wired. This scaffold receives documentation checks only. Scaffold work does
not authorize deployment. No runtime changes or changes to the closed evaluation.

## Discovery and open M0 work

`_download.py` has unfiltered, filtered and file-like/NoDir CSV branches. Confirm
which virtual paths remain reachable under retirement policy. The active filter
contract currently references environment-backed enablement and row caps; the CSV
surface needs an explicit amendment, with other consumers preserved.
The wepp1 overlay uses eight browse workers and a 120-second Gunicorn setting;
the standalone harness has 180-second staging/conversion ceilings. Verify actual
ASGI/proxy timeout semantics and resource budgets rather than copying defaults.
Standalone unsupported schemas/codecs are release blockers where currently valid.

## Validation and handoff

Scaffold validation: six Markdown files passed lint with zero errors/warnings;
spelling previews and whitespace checks passed.
Runtime tests, independent reviews, binary/image builds and deployment: not run.
Next: execute M0 of the active plan when implementation is requested. Retain exact
contract/binary/source identities, generated HTTP byte readback, no-fallback proof,
shared-worker admission and crash/disconnect evidence before any cutover claim.
