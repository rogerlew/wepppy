# Correctness and User-Experience Review - RQ operation webhooks

## Metadata

- Package: `20261027_rq_webhooks`; date: 2026-10-28.
- Independent reviewer: `/root/contract_correctness`.
- Context: implementation descending from ratified checkpoint `6ba2d8d9d`.
- Authority: `docs/schemas/rq-webhook-contract.md`, admission, membership/settlement,
  delivery/recovery sections; ADR-0109. Security: [review](20261028_security_review.md).
- Detailed findings/disposition: [implementation reviews](20261028_implementation_reviews.md).

## User Outcome

Clients optionally request an execution-completion callback with an idempotent
submission. Existing polling/domain-result retrieval remains authoritative for
model success. Same-key retry preserves the planned/accepted operation; delivery
failure does not change computation. Unknown publication or producer closure never
becomes a fabricated successful event. This is a feature implementation, not a
class-wide incident repair; observed preexisting fixture/workflow issues are retained
separately and were not changed to make callbacks succeed.

## Valid-State Matrix

| State | Valid? | Required behavior | Direct evidence |
| --- | --- | --- | --- |
| Callback absent / never used | Yes | Existing response/computation/artifacts | 3,020 broad targeted passes (223 skipped); actual disabled WEPP baseline |
| Callback present but empty/null | No | Explicit 400 before mutation | Admission option tests |
| Valid populated intent / authorized replay | Yes | Same identity, pending 202 or accepted receipt | Real Redis API/replay tests; actual API workflows |
| Existing untracked jobs / disabled feature | Yes | No inferred subscription; no-callback workflow preserved | Worker/route regressions; actual baseline |
| Mixed worker instrumentation | No for new callback | 503; preserve ordinary computation | Worker inventory admission tests |
| Hostile URL, spoofed metadata, foreign reference | No | Canonical rejection or audited unsafe delivery/unknown state | HTTP, binding, external-reference and TLS probes |
| Partial publication / active producer / lost closure | Expected partial state | Same-key recovery or bounded unknown retention | Redis restart, WATCH races, stop/crash/thread/fork tests |

## User-Reachable Error Policy

| Condition | Result | Rationale |
| --- | --- | --- |
| Invalid/unsupported callback | 400 | Explicit admitted surface and input contract |
| Same key, different content | 409 | Prevent duplicate/redirected intent |
| Pending or retryable admission | 202 with planned job ID | Concurrent replay must not return empty success |
| Expired admission | 410 with not_published or unknown | Preserve proof and safe recovery distinction |
| Principal/global capacity or unavailable instrumentation | 429/503 | Fail new optional admission, preserve computation |
| Ambiguous publication or postcommit receipt read failure | 503 with job ID/same-key guidance | Never claim definite rejection after possible acceptance |
| Postcommit culvert browse mint failure | 202 accepted warning | Retry credentials without another computation |
| Delivery exhausts / outcome unavailable | Sanitized operator audit; polling remains | Best-effort contract, no model mutation |

## Generated Artifact Evidence Chain

| Stage | Direct evidence | Result |
| --- | --- | --- |
| Authenticated request and reloaded intent | `workflow_v6_probe.json`, actual culvert probe; real Redis restart/replay | Pass |
| Prepared model inputs | Actual copied continuous-project `wepp/runs/*` exact byte comparison | Pass |
| Fresh execution output | 388 artifacts per run; typed parquet schema including metadata and exact row multisets | Pass |
| Reports and consumer readback | `workflow_readback_v6.json`, `culvert_mixed_parallel_probe.json` | Pass |
| Client callback | Exact persisted/received bytes, HTTP 204 and three-attempt 503 exhaustion, expired issuing tokens | Pass |
| Mixed domain outcome | 38 finished RQ nodes, one successful model and 35 caught domain failures; callback finished | Pass |

Direct unmocked failure boundaries include real Redis reservation/restart, concurrent
claims, stale scheduling, workhorse timeout/stop/SIGKILL, late thread/fork publication,
nontransactional WATCH pipelines and controlled TLS/DNS/response failures.
Highest supported claim: local artifact/data and callback conformance. No production
deployment or universal configuration/concurrency coverage is claimed.

## Findings, Verdict and Sign-off

Independent source review: **pass**, no remaining high/medium findings. The final
WATCH-pipeline fix preserves ordinary errors/repeated saves and marks unsupported
nontransactional tracking incomplete. Existing positive process-containment evidence
is reused; uncertain producers still require bounded positive rechecking.

109 final real-boundary tests passed, including generation continuity, first publication and missing/recreated jobs. Generic
worker and API tests complement actual model evidence. The full suite's unchanged
roads publication-provenance failure is documented, not silently waived or repaired.
Performance remains an explicit acceptance gate; source review does not override it.

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
