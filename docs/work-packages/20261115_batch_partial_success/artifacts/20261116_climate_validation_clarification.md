# Climate validation checkpoint addendum

2026-11-16 06:48 UTC. Parent checkpoint: 390108471.

During implementation review, the owned producer
`wepppy/nodb/wepp_nodb_post_utils.py::ensure_hillslope_interchange` proved that
single-storm runs intentionally omit H.loss and use H.pass. The original blanket
H.loss predicate contradicted the approved requirement to preserve supported
working modes. The operator's “i approve. proceed with commit and implementation”
authorizes preserving those existing modes; this correction does not introduce a
new mode, scientific formula, parameter, fallback, or output schema.

Canonical correction: read actual leaf climate mode, require H.pass for supported
single-storm hillslopes, preserve H.loss for continuous climate. Structurally valid
empty optional/event artifacts do not invalidate required consumer results.

Independent read-only correctness review `/root/contract_correctness` passed at
06:47 UTC; independent security review `/root/contract_security` passed at 06:48
UTC. Both reviewed canonical SHA-256
`d8a6b8aa8284ea7288e95f017ae699987ac3787fa463b47176beb3679e153eb0`.
No medium/high clarification findings. Both verified the actual owned producer;
security confirmed no change to member authorization, path or credential policy.
Implementation of the climate-specific predicate follows this addendum commit.
Runtime verification and full implementation reviews remain pending.
