# Parquet CSV CLI tracker

**Updated**: 2026-11-18 UTC
**Phase**: Closed locally; standalone accepted, integration and broad gate deferred
**Security impact**: high; independent security review retained
**Plan**: [implementation_execplan.md](prompts/completed/implementation_execplan.md)

## Task board

- [x] Commit scaffold (`11ace80c8`) and register isolated work package.
- [x] M0: Ratify contract/ADR, dependency assessment and independent reviews.
- [x] M1: Implement bounded Rust CLI and prove generated CSV byte parity.
- [x] M2: Implement async Python harness, cross-process admission and lifecycle tests.
- [x] M3: Compare Python, native PyArrow and Rust+harness on retained real inputs.
- [x] M4: Close correctness/security findings and record standalone decision.

## Decisions

- Contract-first checkpoint ancestor: `f38f8a4bd9d08b8582fbca8dcd7284a2eef87fb2`.
  Metrics amendment: `23461db5698343605a135e88ca177edaf7fac50d`.
  Metadata/oracle amendment: `bba939a47b499fd6b74327cd6817bdee741a13bb`.
- All Parquet is untrusted even if WEPPpy generated it. The durable contract's
  **Zero-trust input policy** records the operator decision and rationale. Hidden
  index columns and empty files receive the same validation as exported columns.
- One synchronous Rust executable and stdlib async harness; no new service.
  Resource limits only tighten; completed artifacts retain their admission slot.
- Native PyArrow is faster but differs in CSV bytes. Preserve contracted Python
  3.12 formatting; do not trade compatibility for its measured speed.
- WEPPpy integration requires a separately authorized successor even after success.
  No routes, runtime configuration, production exporters or project data changed.

## Gate status and evidence

[Decision](artifacts/decision.md) records performance/resource acceptance, exact
build identity and exclusions. [Validation](artifacts/validation.md) records focused
checks and the separate broad-suite disposition. Independent
[correctness](artifacts/20261118_correctness_review.md) and
[security](artifacts/20261118_security_review.md) reviews have no unresolved
medium/high source findings; integrator closeout attaches final evidence to their
conditional source verdicts. No remote integration, publication or deployment claim.

- Operator decision, 2026-11-18: broad repository pytest is deferred until after
  WEPPpy integration. The in-progress broad run was stopped; no full-suite pass
  or standalone regression is inferred from its cancellation-induced failure.

## Remaining integration work

A successor must handle required unsupported types/codecs/metadata, filters and
archive adapters, service-wide admission across workers, HTTP/auth contracts,
artifact visibility and cleanup, production identity/mount/workflow tests and
rollout/recovery. Parent SIGKILL recovery and per-root budgets remain explicit
standalone limitations. The final audit retains the Chrono maintenance warning.

## Tooling feedback

The installed wctl wrapper selects its installation checkout for documentation.
Use `wctl --project-dir "$PWD" doc-lint --path ...`; initial calls without the
override validated zero new files. Pytest uses `--checkout` and retained receipts.
Rust sources and ignored binaries need explicit provenance beyond Python-oriented
source fingerprints. The broad suite ran against frozen source; final isolated
tooling fixes receive their own exact-binary focused validation.

Task branch: `codex/parquet-csv-cli-package` in
`/home/workdir/wepppy-parquet-csv-cli-package`. Shared-master WIP was untouched.

## Closeout

Implementation commit: `fe82d99d5c5ec2bae60733e1c491f0cadebd9c58`. Final checks: 94 canonical Python tests,
13 Rust tests, formatting, Clippy, documentation lint and changed-file exception
enforcement passed. The rebuilt binary matches all retained benchmark/readback
evidence. Plan archived under `prompts/completed/`; no runtime integration.
