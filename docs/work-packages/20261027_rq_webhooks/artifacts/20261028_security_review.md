# Security Review - RQ operation webhooks

## Metadata

- Package: `20261027_rq_webhooks`; date: 2026-10-28.
- Independent reviewer: `/root/contract_security`.
- Context: implementation descending from ratified checkpoint `6ba2d8d9d`.
- Scope: four admission routes, unsupported-route guards, lineage/hooks/worker,
  Redis receipts/claims, independent HTTPS sender, recorder/playback and Compose.
- Related: [correctness review](20261028_correctness_review.md),
  [review dispositions](20261028_implementation_reviews.md),
  [acceptance matrix](acceptance_matrix.md). Separate QA artifact: N/A.

## Security Triage Decision

Impact: **high**; dedicated review required. New authenticated outbound URL input,
Redis capability storage, queue instrumentation and independent network delivery
cross security boundaries. Assumptions: server code/RQ producers and Redis are
trusted; clients and destinations are untrusted; ordinary run/feature authorization
continues to govern admission/replay. Optional absence and existing untracked jobs
remain valid. Empty/malformed callback input is explicitly invalid.

## Findings

| ID | Severity | Surface | Required action and evidence | Status |
| --- | --- | --- | --- | --- |
| SEC-01 | High | SSRF/TLS | Reject special IPv4/IPv6 forms, mixed public/private resolution, redirects and invalid TLS; pin selected public peer. HTTP tests and `https_probe.json`. | Resolved |
| SEC-02 | High | Capability capture | Strip callback/idempotency fields and raw/truncated/BOM body previews; executed playback never reuses recorded destination. Recorder/playback regressions. | Resolved |
| SEC-03 | High | Admission/restore | Fence publication and claims to actual Redis process/intent; credential-free receipt and typed principal. `restart_restore_probe.json` and API tests. | Resolved |
| SEC-04 | Medium | Capacity/fairness | Account bounded receipts/audits, release principal/member quota, rotate later principals, preserve newer retry deadlines. Real Redis regressions. | Resolved |
| SEC-05 | High | Producer closure | Execution-bound poison, retained thread/fork ownership and positive containment; independent correctness review and real process tests. | Resolved |

No accepted-risk exception or unresolved high/medium security finding is claimed.

## Surface Checks

- Valid/hostile states are separated in the correctness matrix; real authenticated
  WEPP and culvert submissions exercise valid admission, TLS and model boundaries.
- Existing auth/scope/feature/CSRF behavior is preserved. Browse minting is not
  persisted; postcommit failures retain same-key recovery and job identity.
- No new dependency, signing infrastructure, bearer forwarding or raw destination
  logging. Dispatcher mounts Redis credentials only; no Docker socket or run write
  capability is added. Capture and operator inspection omit URL path/query.
- DNS, connection, TLS and response handling share a subprocess total deadline;
  bounded headers and fixed error vocabulary prevent response/error disclosure.
- Fixture sources are read-only, writable roots are owned, private keys remain
  ignored. Receiver/dispatcher stay isolated; the batch worker alone has ordinary
  model-data egress for USDA. No production deployment occurred.
- Restores/copies are disarmed until external process-identity reauthorization.
  Pause, admission disable, retention and recovery are documented for operators.

## Verdict and Sign-off

Independent source security review: **pass**, high 0 / medium 0 unresolved.
Release recommendation: **local implementation acceptance passed**; production activation is separate.
This security approval does not replace correctness, artifact parity or the
approved performance limit. No exhaustive-coverage claim is made.

### Final performance-related source review

Both independent reviewers passed batching the pre-fork start receipt with the
existing metadata transaction and sharing the 100 ms evaluator scheduling budget
across active roots, rotating after each bounded generator step. Ordinary RQ
errors, producer closure, retry deadlines and final generator cleanup are preserved.
The slice is cooperative: an in-flight bounded step may finish after its deadline.
Ten process-boundary tests and three scheduler regressions passed. No high/medium
source findings remain; performance acceptance is separately required.

### Generation and publication findings: closed

Both independent reviewers confirmed closure of failed-bookkeeping ABA, missed
overlapping attempts, hash deletion/recreation and missing first publication proof.
The ordinary pre-fork write preserves current/predecessor generation; first
publication seeds unstarted exactly once; discontinuities are sticky incomplete.
Current generation is fenced with actual job state. Missing hashes remain unknown.
Root publication checks preserve computation acceptance while suppressing unsafe
notification proof. Known older registered producers retain their exit obligation.

The late-WATCH proposal was rejected; active-page early return retains early fences
for every potential terminal page. A stale terminal due repair prevents principal
starvation. Prior zero-attempt backlog artifacts are evaluator-only diagnostics;
final measured sender overlap is mandatory. No high/medium source finding remains
after the final publication review; acceptance is still a separate gate.

## Final local acceptance sign-off

Both independent reviewers confirmed the final canonical six-default/four-batch
fixture evidence. Runtime source is committed at `62b272a6c`; no high/medium finding
remains. Final gates: 109 real-boundary tests; 3,020 targeted passes/223 skipped;
actual v6 WEPP artifact parity and post-expiry delivery; parallel mixed culvert
38 finished nodes, one model success and 35 caught failures.

Both reviewers independently recomputed 1,000-transition p95: 75.064 → 75.701 ms,
+0.849% / +0.637 ms, with 11 receiver observations during timing and 15 audited
attempts. The earlier single-batch and zero-sender limitations are superseded by
these final results, not waived. The full-suite roads provenance failure remains
an explicitly isolated baseline issue. Local acceptance passes; production
deployment/activation is outside this package's authority.
