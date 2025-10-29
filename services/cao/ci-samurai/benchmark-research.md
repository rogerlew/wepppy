# CI-Maintenance Agents — GPT‑5 Comparison Research

> Scope: Public agents, playbooks, confidence heuristics, telemetry strategies. Tailored adoption notes for CI Samurai.

## Summary

- Focus areas: dependency/security updaters, merge-queue/gating bots, CI triage/flake bots, automated repair/fix systems, and telemetry/analytics.
- Immediate adoptions: Dependabot compatibility-score gating for safe automerge; Mergify/queue-style speculative validation; flake heuristics and quarantine; Repairnator-style patch validation loop; PR report structure inspired by Dr.CI and Prow Triage.

## Benchmarked Systems

### 1) Dependency & Security Update Bots

- GitHub Dependabot
  - Playbook: Periodic PRs for dependencies and security advisories; optional automerge via repo rules.
  - Confidence heuristics: Compatibility score (pass rate from public repos), ecosystem-aware versioning (semver), vulnerability severity signal.
  - Telemetry: PR metadata (compatibility score), advisory linkage, GH Insights. Docs: https://docs.github.com/code-security/dependabot
  - Adopt: Use “compatibility score analog” by tracking CI Samurai PR merge outcomes per change type to tune thresholds.

- Renovate Bot
  - Playbook: Scheduled updates, grouping, rate limiting, rebase/branch automerge; extensive policy via config.
  - Confidence heuristics: stabilityDays/minimumReleaseAge; status-check gating; risk via semver, source trust; grouping major updates.
  - Telemetry: Built-in logs; self-hosted exposes metrics, dashboards. Docs: https://docs.renovatebot.com/
  - Adopt: Borrow stability windows (require green across N consecutive validations) and strict status-check gating before PRs.

- Snyk/Dependabot Security Fix PRs
  - Playbook: Open PRs with minimal patches; fix suggestions.
  - Heuristics: CVE severity thresholds; minimal-diff bias.
  - Telemetry: Advisory linkage, PR labels. Docs: https://docs.snyk.io/; https://docs.github.com/code-security/dependabot/dependabot-security-updates
  - Adopt: Treat security-related failing tests as high-priority; prefer minimal, reversible diffs.

### 2) Merge Queue / CI Gating

- Mergify (and GitHub Merge Queue)
  - Playbook: Queue PRs; speculative checks on merge commits; batch/bisect to keep main green.
  - Heuristics: Rule engine (labels, owners, paths), priorities, required checks, batching size; backpressure for flaky CI.
  - Telemetry: Queue depth, wait times, success/failure per rule. Docs: https://docs.mergify.com/
  - Adopt: “Speculative validation” — validate PR as-if-merged into latest master before proposing fixes; batch related changes.

- Bors‑NG (Rust’s gatekeeper)
  - Playbook: Only merge PRs that pass integration on a merge-commit; optional try-builds.
  - Heuristics: Strict status gates; serialization to prevent inter-PR interference.
  - Telemetry: Build results per batch. Docs: https://bors.tech/; https://github.com/bors-ng/bors-ng
  - Adopt: Serialize high-risk fixes; favor merge-commit validation in the isolated workspace.

- Prow/Tide (Kubernetes CI)
  - Playbook: Label-driven automation, merge pool (Tide), prow-commands, autoresponses.
  - Heuristics: Label/owner/rule evaluation; retry for flakes; quarantine.
  - Telemetry: Triage dashboard, Spyglass artifacts. Docs: https://github.com/kubernetes/test-infra/tree/master/prow
  - Adopt: Label conventions for CI Samurai (“ci-samurai-regression”, “needs-guidance”), and automated reruns + quarantine.

### 3) CI Triage, Flake Detection, PR Summaries

- Google FlakyBot (GitHub App)
  - Playbook: Detect flaky tests from CI artifacts; auto-file issues and annotate PRs.
  - Heuristics: Failure/pass alternation across reruns; thresholds per test.
  - Telemetry: Issue labels, occurrence counts, links to logs. Example: https://github.com/googleapis/repo-automation-bots/tree/main/packages/flakybot
  - Adopt: Add flake classification and auto-issue filing with counts and last-seen.

- Chromium Sheriff-o-Matic
  - Playbook: Cluster similar failures across builders; highlight top offenders for the “build sheriff.”
  - Heuristics: Signature clustering on logs and stack traces; frequency/rate-of-change.
  - Telemetry: Dashboards of clusters, trendlines. Docs: https://chromium.googlesource.com/infra/infra/+/refs/heads/main/appengine/sheriff-o-matic/
  - Adopt: Stack-trace fingerprinting to group failures, with frequency-based prioritization.

- PyTorch Dr.CI
  - Playbook: PR comment summarizing CI failures with links and suggested owners.
  - Heuristics: Rule-based failure parsing → actionable summary.
  - Telemetry: PR comment history, failure categories. Source: https://github.com/pytorch/test-infra (drci)
  - Adopt: Reuse “Problem/Root Cause/Solution/Testing/Confidence” PR blocks and inline links to logs/tests.

### 4) Automated Program Repair / Auto‑Fix Systems

- Repairnator (Inria)
  - Playbook: Monitor CI failures; reproduce failing build; run repair tools; validate with tests; open PR with patch.
  - Heuristics: Patch ranking; require exact reproduction before attempting repair; only propose if tests pass post‑patch.
  - Telemetry: Build reproduction success rate, patch validity, time to fix. Paper: https://arxiv.org/abs/1810.01791 — Code: https://github.com/repairnator/repairnator
  - Adopt: Enforce reproduce→fix→revalidate loop; rank multi-candidate patches and pick top‑1.

- Meta SapFix/Getafix
  - Playbook: Mine human fixes (Getafix) and synthesize patches (SapFix); submit diffs for review.
  - Heuristics: Pattern mining, patch ranking, minimal-diff preference, human approval gate.
  - Telemetry: Per‑pattern success rates, review outcomes. Blog: https://engineering.fb.com/2019/06/12/developer-tools/sapfix/; https://engineering.fb.com/2018/08/08/developer-tools/getafix/
  - Adopt: Maintain a “fix pattern” catalog (missing mocks, path joins, timezone, race sleeps) and track success by pattern.

- Code Scanning Autofix (GitHub Copilot/CodeQL)
  - Playbook: Generate PRs fixing security issues with suggested patches and tests/examples.
  - Heuristics: Severity/rule confidence; rule‑specific fix templates.
  - Telemetry: Rule hit rates, autofix acceptance. Docs: https://docs.github.com/code-security/code-scanning/automatically-fixing-code-scanning-alerts
  - Adopt: Treat static-analysis regressions as first‑class with rule‑aware fix suggestions.

- OpenRewrite/Moderne
  - Playbook: Recipe‑based safe refactors across large codebases, run in CI.
  - Heuristics: Type‑checked rewrite rules; guardrails on scope.
  - Telemetry: Recipe success rates, diff sizes. Docs: https://docs.openrewrite.org/
  - Adopt: Encode common refactors (pytest assertions, logging, deprecations) as recipes runnable by CI Samurai.

### 5) Telemetry & Test Analytics Platforms

- Buildkite Test Analytics
  - Signals: Test duration, flake rate, failure reasons, ownership signals, trends.
  - Adopt: Emit per‑test spans with duration/outcome and flaky bit; store in Redis→Go status2→dashboards.
  - Docs: https://buildkite.com/test-analytics

- Datadog CI Visibility / CircleCI Insights / GitHub Actions Test Reporting
  - Signals: Step and test spans; trace‑ID linked logs; failure clustering; duration regressions.
  - Adopt: Structured events for steps/tests with trace IDs; emit to Redis DB 2 and persist summaries to NoDb JSON.
  - Docs: https://docs.datadoghq.com/continuous_integration/; https://circleci.com/docs/insights/

- Launchable (Test Impact/Selection)
  - Signals: ML‑ranked tests for each change; speed vs confidence trade‑off.
  - Adopt: For revalidation cycles, prioritize high‑signal tests first to fail fast. Docs: https://www.launchableinc.com/

## Heuristics To Adopt (CI Samurai)

- Multi‑run confidence: Require 2+ consecutive green validations for medium‑risk fixes (Renovate stabilityDays analog).
- Compatibility‑score analog: Track acceptance rate by fix pattern/path to determine thresholds for when to auto‑open vs only file an issue (Dependabot compatibility score analog).
- Speculative validation: Validate as‑if merged with latest master before proposing PR (Mergify queue).
- Flake classification: Auto‑rerun up to N times; mark flaky if pass occurs within retries; quarantine and open tracking issue (FlakyBot best‑practice).
- Patch ranking: When multiple fixes are viable, score by minimal diff, locality (single file), and prior pattern success (Repairnator/SapFix).
- Minimal‑diff bias: Prefer targeted edits and avoid cross‑cutting changes unless high confidence and validated.

## Telemetry Strategy (Mapping to wepppy)

- Event schema
  - run: id, start/end, git sha, branch
  - test: file::name, duration_ms, outcome, retries, flaky
  - failure: signature hash, stack summary, category (mock/import/assertion/timeouts)
  - action: proposed_fix_id, pattern, diff_size, files_changed, confidence
  - outcome: pr_number, merged_with_edits|merged|closed, reviewer_feedback

- Pipeline integration
  - Publish structured events to Redis DB 2 via StatusMessengerHandler; stream via services/status2; persist NoDb JSON in DB 13 for 72h.
  - Artifacts: attach parsed pytest and npm test JSON, failure signatures, and diffs.

- Dashboards
  - Flake rate per test/module over time; top failure clusters; PR acceptance by pattern; time‑to‑green.

## Playbooks To Borrow

- Dependency updates: Grouped PRs with stability window; automerge for patch/minor when tests green.
- CI gating: Merge‑queue semantics for agent PRs; serialize risky fixes; batch when safe.
- Flake management: Auto‑rerun, quarantine, issue creation with counts and owners.
- Automated repair: Reproduce → patch → revalidate; only propose if full suite passes; include thorough PR template.
- PR communication: Dr.CI‑style concise PR comment with links to logs, failing tests, and owner suggestions.

## Adoption Plan (Phased)

1) Telemetry foundation: emit structured test events; add failure fingerprinting; basic dashboard.
2) Confidence scaffolding: pattern catalog, outcome tracking, thresholds per pattern/path.
3) Safe playbooks: dependency fixes and test‑only repairs with stability windows and queue validation.
4) Advanced: patch ranking across multi‑candidate fixes; quarantine automation; merge‑queue semantics.

## References

- Dependabot: https://docs.github.com/code-security/dependabot
- Renovate: https://docs.renovatebot.com/
- Mergify: https://docs.mergify.com/
- Bors‑NG: https://github.com/bors-ng/bors-ng
- Prow/Tide: https://github.com/kubernetes/test-infra/tree/master/prow
- FlakyBot: https://github.com/googleapis/repo-automation-bots/tree/main/packages/flakybot
- Sheriff‑o‑Matic: https://chromium.googlesource.com/infra/infra/+/refs/heads/main/appengine/sheriff-o-matic/
- PyTorch Dr.CI: https://github.com/pytorch/test-infra
- Repairnator: https://github.com/repairnator/repairnator
- SapFix/Getafix: https://engineering.fb.com/2019/06/12/developer-tools/sapfix/ ; https://engineering.fb.com/2018/08/08/developer-tools/getafix/
- GitHub Code Scanning Autofix: https://docs.github.com/code-security/code-scanning/automatically-fixing-code-scanning-alerts
- OpenRewrite: https://docs.openrewrite.org/
- Buildkite Test Analytics: https://buildkite.com/test-analytics
- Datadog CI Visibility: https://docs.datadoghq.com/continuous_integration/
- Launchable: https://www.launchableinc.com/

