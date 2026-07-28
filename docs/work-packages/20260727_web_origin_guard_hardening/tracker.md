# Tracker – Web Same-Origin Guard Parity and Data-Boundary Hardening

> Living document tracking progress, decisions, risks, and communication for this work package.

## Quick Status

**Timezone**: UTC
**Started**: 2026-07-27 23:40 UTC
**Current phase**: Contract checkpoint commit
**Last updated**: 2026-07-28 00:45 UTC
**Next milestone**: Record WP00 standalone checkpoint revision, then WP01
**Security impact**: `high`
**Dedicated security review**: `yes`
**Security artifact**: `docs/work-packages/20260727_web_origin_guard_hardening/artifacts/<date>_security_review.md`

## Task Board

### Ready / Backlog
- [ ] WP00 - Register the bounded remediation; finalize the contract decision
  and canonical amendments; obtain dual independent checkpoint reviews;
  disposition findings; commit and record the documentation-only ancestor
  (`prompts/active/wp00_contract_checkpoint.prompt.md`)
- [ ] WP01 — Same-origin guard parity: normative contract + align all three guards; query-engine gains the `Sec-Fetch-Site` fast-path (fixes the bearhive upload 403); harden forwarded-header trust and `Origin` conflict handling; shared test vectors (Codex; `prompts/active/wp01_same_origin_parity.prompt.md`)
- [ ] WP02 — Scope reset cookie-clear targets to WEPPcloud-owned names/domains (Codex; `prompts/active/wp02_cookie_clear_scoping.prompt.md`)
- [ ] WP03 — Allowlist-based diagnostics Copy JSON report; drop arbitrary backend error text and absolute WS hostname (Codex; `prompts/active/wp03_report_redaction_allowlist.prompt.md`)
- [ ] WP04 — CSRF-enabled same-origin/header test matrix across all three surfaces (Codex; `prompts/active/wp04_same_origin_test_matrix.prompt.md`)
- [ ] Security review artifact (Codex or Claude Code) before closure
- [ ] Contract doc extension in `docs/schemas/weppcloud-csrf-contract.md` (Claude Code; can land with WP01)

### In Progress
- [ ] Umbrella execution governed by
  `prompts/active/web_origin_guard_hardening_execplan.md`

### Blocked
- (none)

### Done
- [x] Package scoped and scaffolded (2026-07-27 23:40 UTC)
- [x] WP00 governance registration, contracts, dual independent reviews, and
  disposition passed with zero unresolved findings (2026-07-28 00:45 UTC)

## Sequencing

WP00 first; it creates the mandatory reviewed contract ancestor. WP01 begins
only after the checkpoint revision is recorded below. WP02/WP03 are independent
after WP01. WP04 lands last so its matrix exercises final behavior. Independent
final security and correctness reviews follow WP01-WP04, before closure.

**Checkpoint revision**: pending

**Bounded-remediation authority**: REM-04 / GOV-00A-M1D (checkpoint candidate)

## Decisions Log

### 2026-07-28 00:00 UTC: Add the missing contract-first execution phase

**Context**: The initial scaffold introduced new normative origin, cookie, and
report behavior but contained no contract-decision artifact, bounded-remediation
registration, dual checkpoint review, or standalone ancestor.

**Decision**: Add WP00 and an umbrella ExecPlan. Make the recorded checkpoint
revision a hard dependency of every production edit.

**Impact**: The package is executable without bypassing the repository's
contract-first standard. Implementation remains blocked until WP00 completes.

### 2026-07-27 23:40 UTC: Query-engine is the outlier; align to a single contract rather than three ad-hoc guards
**Context**: Three same-origin guards exist — Flask `_is_same_origin_post`, rq-engine `_is_same_origin_cookie_request`, query-engine `_is_same_origin_request`. The first two accept `Sec-Fetch-Site: same-origin` up front; query-engine does not, so a same-origin upload POST 403s behind upstream TLS (verified on `wc.bearhive.duckdns.org`; passes on `wepp.cloud` only because Caddy terminates TLS there and `{scheme}` = `https`).

**Decision**: Define one normative same-origin contract and conform all three guards to it (Flask/Starlette request objects differ, so this is a shared contract + shared test vectors, not necessarily a shared function). The contract adds the `Sec-Fetch-Site` fast-path to query-engine and tightens forwarded-header trust and `Origin`-conflict handling in all three (per independent-review finding 2).

**Impact**: Fixes the live symptom at the application layer independent of proxy topology; the Caddy scheme fix is a separate operational companion.

### 2026-07-27 23:40 UTC: Infra and UX kept out of the security package scope
**Context**: The bearhive 403 has an infra root cause (Caddy forwards `X-Forwarded-Proto {scheme}` = `http`) and a UX symptom (a 403 rendered as an "Upload speed" warning).

**Decision**: Neither is a code WP here. The Caddy fix is an operational companion (needs node-owner consent + terminator CIDR). The upload-probe relabel is a related follow-up to `20260727_diagnostics_page_ux`. This package makes the *application* correct and robust; the companions harden the deployment and the display.

## Risks and Issues

| Risk | Severity | Likelihood | Mitigation | Status |
|------|----------|------------|------------|--------|
| Parity change weakens a guard (too-permissive Sec-Fetch-Site, forwarded-header spoofing) | High | Low | Security review gate; contract requires Origin-conflict rejection and proxy-normalized origins | Open |
| Behavioral drift between three implementations after change | Medium | Medium | Shared test vectors (WP04) asserted against all three | Open |
| query-engine change regresses other bandwidth/query endpoints | Low | Low | Change scoped to the same-origin helper; run query-engine suite | Open |
| Canonical session contract retained legacy raw forwarded-origin trust | High | Low | Reconciled contracts; legacy switch inert; required negative regression | Closed by dual rereview |

## Verification Checklist

### Code Quality
- [ ] `wctl run-pytest` for affected weppcloud + query-engine + rq-engine suites
- [ ] `wctl run-npm lint` / `wctl run-npm test`

### Security
- [ ] Dedicated security review artifact present and complete
- [ ] No guard accepts a request whose `Origin` conflicts with the page origin
- [ ] Forwarded-header trust cannot admit an attacker-supplied origin
- [ ] No unresolved medium/high findings

### Documentation
- [ ] Contract-decision artifact complete
- [ ] Bounded remediation registered in Pure UI governance artifacts
- [ ] Two independent checkpoint reviews passed and dispositioned
- [ ] Standalone checkpoint revision recorded and verified as ancestor
- [ ] `docs/schemas/weppcloud-csrf-contract.md` extended with the same-origin contract + test vectors
- [ ] Package closure notes complete

### Deployment
- [ ] Verified on a local stack and on an upstream-TLS topology (or a simulated one) that same-origin POST is authorized

## Progress Notes

### 2026-07-28 00:00 UTC: Scaffold made contract-first executable

**Agent/Contributor**: Codex

**Work completed**:
- Added an active umbrella ExecPlan with ordered milestones and acceptance
  evidence.
- Added WP00 for governance registration, contract amendment, dual review,
  disposition, and the standalone ancestor.
- Added a draft contract-decision artifact that identifies the unresolved
  decisions without claiming implementation authority.
- Made WP01-WP04 explicitly dependent on the recorded checkpoint revision.

**Next steps**: Execute WP00. Do not edit implementation files until its reviewed
checkpoint commit is recorded here.

### 2026-07-27 23:40 UTC: Package scaffolded
**Agent/Contributor**: Claude Code

**Work completed**:
- Scoped from the diagnostics independent security review (findings 2/4/10) plus the upload-403 root-cause investigation (query-engine missing the `Sec-Fetch-Site` fast-path).
- Confirmed the three-guard divergence against source (Flask `:357`/`:327`, rq-engine `:291`/`:259`, query-engine `:206`/`:177`).
- Authored package.md, tracker.md, and WP01-WP04 prompts.

**Next steps**: Codex executes WP01. Claude Code extends the CSRF contract doc alongside.

## Communication Log

### 2026-07-27: Package initiated
**Participants**: Roger Lew, Claude Code
**Topic**: After the diagnostics review and the upload-probe 403 investigation, Roger asked to scaffold the security work package for the logged follow-ups.
**Outcome**: This package.
