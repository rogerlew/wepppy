# RQ admin catalog monitoring

The operator requested dedicated catalog admission and health panels on
`rq/info-details` following the persistent observer pause incident. Base
revision is 65dfaa0e9. Implementation conformance is pending.

The additive decision is in the query engine catalog refresh contract under
“Admin admission and health snapshot”. The existing static Admin/Root page
remains the authorization boundary. Operators need to see simultaneous blockers
and evidence of progress without loading project data. Restrict telemetry to
operational counters, timestamps, bounded identifiers and pause lifetime.
Verify disabled, empty/legacy, active, paused with expired jobs, partial and
malformed state. Verify panel rendering and existing job views. The scheduler
summary is additive and older producers may omit it.

Independent correctness and security reviewers passed the checkpoint on
2026-11-21 UTC. Preserve simultaneous blockers, unknown telemetry, read-only
Redis access and locator-count semantics. Only recognized operational pause
labels can be disclosed. Show a generic owner for all other values, including
tokens and private paths. Cover role denial and hostile Redis values.
