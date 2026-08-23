# WBT serialization addendum review disposition

Focused real-RQ validation after the original dependency checkpoint showed that
the prior WBT request tail to the next request's build is an independent-request
serialization edge, not a required-output edge. The addendum retains failure
tolerance only on that prior-tail edge and keeps each request's
`build_subcatchments_rq` to `abstract_watershed_rq` edge strict.

| Review concern | Disposition |
| --- | --- |
| WBT serialization purpose was conflated with resource throttling | The matrix now distinguishes resource bounds from same-resource mutation ownership. |
| A failed predecessor may leave partial run state | The later request must reconstruct and validate state under the admission and directory-root locks and must not consume predecessor output. |
| Original operator approval was attributed to the later WBT classification | The original two-exception decision remains historical; the WBT addendum is recorded separately as an evidence-driven Codex classification. |
| The prior security assessment omitted the new edge | The assessment now covers partial state, ownership locks, admission races, and the strict build-to-abstraction child. |

Independent correctness/governance and security reviewers approved the amended
checkpoint on 2026-08-23 with no remaining High or Medium findings. This review
approves the documentation contract; implementation still requires focused
real-RQ proof, production-path lock/state conformance, broad validation, and
post-implementation review.
