# Production common-image vulnerability remediation

Opened 2026-11-23 UTC. **Production release held.** Roger Lew owns the open residual-risk decision. [Release decision](artifacts/20261123_release_decision.md)

Produce one release decision for the common image serving wepp1, wepp2 and wepp3. The catalog rollout introduced zero new advisory matches, but the serving image carries inherited findings. Use independently reviewable dependency commits so a compatibility failure can be traced to its repair batch. The release candidate combines the accepted batches.

## Baseline and authority

The reference is source `dacf4185d945f9700a235ac23fb1b99623cf11e6`, image `sha256:b6e0462f8a749eabb168ea398a4f8056c46305f2a003e04b026c0d5623567c94`, scan manifest `7ca36f0d9efd701de7c831215d07eb6d4852278d05b64751191d6d2ef67450e3`. Grype reported 87 critical and 679 high matches. The separate npm audit included four high findings. Record subsequent baseline changes explicitly. The prior image acceptance applies to that image alone.

Reuse the [dependency security package](../20261110_wepp1_dependency_security_gate/package.md), [evidence contract](../../infrastructure/dependency-security-evidence.md), [dependency policy](../../adrs/ADR-0140-dependency-security-gate-policy.md) and [release policy](../../infrastructure/production-deployment-policy.md). Scientific native coverage, upstream backports, bundled libraries, cached copies and advisory aliases require artifact-specific evidence. Retain raw evidence under the existing private deployment evidence store.

## Completion

Deliver a disposition for each in-scope finding under the existing policy, tested repair commits, a same-database comparison for the final image, and an operator-readable release recommendation. Report outstanding applicable known-exploited findings, fixable applicable critical/high findings, expiring exceptions and native coverage gaps. Record any hold, risk owner and next action. Report production activation separately if authorized.

Security impact is high. Independent security and correctness reviewers assess the exact candidate and record dated reviews in this package before closeout. The production operator owns release risk acceptance. Complexity budget covers dependency pins, bounded compatibility changes, build inputs, tests and evidence using the existing pipeline. Changes to service topology or scientific behavior require separate justification.

[Execution plan](prompts/active/implementation.md) · [Tracker](tracker.md)
