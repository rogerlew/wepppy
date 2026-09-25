# Dead Horse Creek GridMET follow-up audit

Status: Closed, 2026-09-17 UTC; package date is 2026-09-16 Pacific.

## Scope and decision

The owner reran CLIGEN with GridMET observed and then M3 on thespian-cleanness.
Audit the new saved attempt f493a714df9d4fbfbfd4370c46ad54f8 and compare with
prior attempt 0a34c96cd0dc4e6bb7bb7780d8f8915b and the August 5–12, 2021
window in Rengers et al. (2024), https://nhess.copernicus.org/articles/24/2093/2024/ .
The prior audit is closed historical evidence and is not rewritten. Distinguish
calendar-dated gridded daily precipitation from measured subdaily storm intensity.

Read-only scope; no run mutations, model or parameter changes, restart or rerun.
Complexity budget: existing tools only, no new dependencies or infrastructure.
Security impact low; no security-boundary change or dedicated review required.
No ADR required. Acceptance: independent arithmetic/rainfall checks, unchanged
predictors, before/after comparison, historical-window extraction, authenticated
report and retained preservation evidence. Document limitations honestly.

[Tracker](tracker.md) · [Plan](prompts/completed/audit_execplan.md)

## Outcome

[Findings](artifacts/findings.md): independent numerical checks pass; P50 is
unchanged and rainfall-frequency scenarios differ. Both source GridMET and CLI
have zero precipitation on August 5–12, 2021, preventing a storm comparison.
The report correctly exposes current=false after an active-CLI ctime change;
its cause is not established. All 266 protected files remain unchanged.
