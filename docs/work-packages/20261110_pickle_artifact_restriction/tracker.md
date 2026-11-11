# Tracker - Pickle artifact restriction

## Quick Status

**Timezone**: UTC
**Last updated**: 2026-11-11 UTC
**Current phase**: M0-M3 complete; M4 awaits separate rollout authorization
**Security impact**: high
**Dedicated security review**: `artifacts/20261110_security_review.md`
**Checkpoint ancestors**: `aeab3c3e1`, supplemental `e2b9f6b35`
**Starting revision**: `991fc5e2c3f1cd2e5d74169e2d7bccb609203924`

## Task Board

- [x] M0: promote Bootstrap/browse/freshness contracts; two independent reviews;
      commit checkpoint before production edits.
- [x] M1: retain focused failing real Git and HTTP regressions.
- [x] M2: remove pickle readers and capability advertisements; add admission and
      HTTP guards; synchronize docs and D-Tale declarations.
- [x] Run approved focused suites: Bootstrap27, browse/files130, D-Tale48.
- [x] Stubtest (2 modules) and test-stub hygiene pass.
- [x] M3: final independent correctness, QA and security approvals; scoped docs checks.
- [ ] M4: separately authorized rollout and controlled production smoke.

## Decisions and discoveries

The approved suffix-only rule, raw-byte preservation, case handling, supported
formats and no-full-suite waiver are durable in the canonical Bootstrap and
browse contracts. The freshness contract explicitly permits the bounded reader
removal. Independent contract review receipts are in
`artifacts/20261110_contract_reviews.md`.

Archive-backed NoDir traversal was already retired. Preserve its existing409/404
responses and whole-archive downloads; exercise physical files under NoDir roots.
The supplemental checkpoint records both reviewers' approval of this correction.

Security review found merges and already-reachable ref tips could bypass the
introduced-commit display. Real pushes reproduced it. A suffix-only per-ref
baseline comparison now checks tips and intermediate introduced commits with
rename detection disabled; general merge/file validation is unchanged. Allowed
text merge/fast-forward controls retain unchanged inherited pickle bytes.

Initial stubtest exposed existing declaration drift; synchronized only the
existing DatasetMeta fields and response helper keyword parameters. No runtime
identity, permissions, authentication or deployment topology changed.

## Validation and review

See `artifacts/20261110_validation.md` for commands, red/green receipts, digest,
limitations and test corrections. 205 focused tests pass. Full Python/frontend
suites are intentionally waived, not claimed as passing. Dedicated correctness,
QA and security artifacts retain findings and final dispositions.

## Timeline

- 2026-11-11 03:50 UTC: source diagnosis and package scaffold.
- 2026-11-11 04:08 UTC: reviewed contract checkpoint `aeab3c3e1`.
- 2026-11-11 04:10 UTC: reviewed archive compatibility checkpoint `e2b9f6b35`.
- 2026-11-11 UTC: focused red/green implementation and merge-bypass correction.
- Pending: explicitly authorized scoped rollout; no production change performed.

## Handoff

The package remains open for M4. Approve the committed implementation candidate
before deploying through the canonical wepp1 entry point. Controlled acceptance:
forbidden Bootstrap push, inert existing pickle listing/no preview/no D-Tale,
415 responses, byte-identical raw download, and supported CSV/Parquet viewing.
Do not upload or execute an executable pickle. Rollback must retain equivalent
admission and HTTP restrictions. Local tests do not establish production parity.
