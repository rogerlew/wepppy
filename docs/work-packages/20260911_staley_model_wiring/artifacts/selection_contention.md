# Selection and recorder contention

Observed 2026-09-11 on populated addicted-reservist/config: ordinary model
selection returned HTTP409/job_active, including error IDs
5308d62bb99842bf94770774ac6e178b and d115d2b5f86f46d9b11e7e9d5caf0e49.
Browser recorded concurrent POST recorder/events. That route uses
helpers.authorize_and_handle_with_exception_factory, which acquires the same
run lifecycle and request fences as rq-engine mutation middleware. No missing,
corrupt or hostile project state was involved. Sources and previous results
remained usable; each rejected selection failed before its route body.

Scope: make the already-accepted serialized preference save tolerate this
explicit pre-admission busy response. No shared-lock exemption, recorder
suppression, automatic job rerun or generic transport retry.

Precedents: hardening-lifecycle-standard.md; NOAA transient retry package
20260429_noaa_atlas14_retry_backoff; existing WCHttp explicit auth-refresh retry.
Reuse bounded, typed-error retry and explicit exhaustion. Unlike downloads or
auth refresh, this handles only selection's explicit job_active before admission.

Mechanism is promoted in model_selection.md, Selection contention paragraph.
Four total attempts, same captured payload, 250/500/1000-ms waits within the
existing preference queue. Visible waiting state, Run disabled. Destruction
cancels further attempts. Final errors remain explicit. No retry for network,
auth, other409, upload or model execution.

Hypothesis: normal recorded selections succeed across short recorder lease
holds within the bounded window. Health: save succeeds, original preference
preserved, recording continues. Danger: exhausted busy responses, changed job
count, unauthorized/nonbusy retries, writes after destruction, or delayed
preferences overwriting newer selections. Stateless recurrence-triggered review:
reopen a scoped incident upon exhaustion or shared admission/recorder changes;
retain this evidence and reassess removal when that collision no longer exists.

Correctness reviewer classified this as a bounded conformance mechanism under
the reviewed serialized-selection behavior and valid-state/noninterference gate,
not a new domain feature/checkpoint. Required regressions: fake-timer exact budget,
negative errors, ordering and destruction; real recording-enabled selection and
reload. Implemented and independently accepted. Fake-timer boundary tests passed;
full npm 872 passed. Recorded live sequence 409/409/409/200 recovered with
recording enabled, followed by successful M1/M3 saves preserving NOAA. Reload
and preflight/download checks passed; see browser_readback.log. No model job
was resubmitted during this readback.
