# Initial Random Roughness Review

Owner: Roger Lew. Started 2026-10-09 (UTC). Status: sensitivity study complete;
low-severity forest default revision accepted in
[ADR-0083](../../adrs/ADR-0083-low-severity-forest-initial-random-roughness.md).
Template and four packaged extended-lookup RRINIT values are now 0.06 m.
See [study results](sensitivity-results.md),
[initial assessment](assessment.md) and [delegated literature review](literature-review.md).

Follow-up: [low-severity forest 4 versus 6 cm](low-forest-4v6-results.md),
112 successful simulations. Runoff and full-record rankings are effectively
unchanged; sandy-loam event-level sediment ordering improves. Roger adopted
the revision as a parameterization inconsistency correction, not a sediment
trade-off. The resulting sediment changes remain documented in the evidence.

Review WEPPpy defaults for forest, young forest, shrub and tall grass under
unburned and burned conditions. Trace rrinit through management serialization
and WEPP Forest consumers; commission a primary-source literature review;
recommend whether and how to run a bounded sensitivity study before revision.

The initial read-only assessment was followed by Roger's authorization to add
canonical young-forest coverage and execute the bounded sensitivity study.
The completed work comprises 896 runs, a 96-case canonical matrix and analysis
compatibility/fixture corrections. No physical model patch, calibration, routing
rewrite, release or deployment occurred. Defaults were unchanged during the
studies; the subsequent approved revision changes only low-severity forest
RRINIT and its packaged extended-lookup mirror. Existing generated-input
precedence and custom project overrides are unchanged. Historical artifacts
remain pre-adoption evidence; their input identities must not be relabeled as
the new default or silently regenerated.

Complexity budget: assessment artifacts plus the authorized bounded grid using
the existing matrix, a reproducible climate fixture generator and compact
analysis/receipt artifacts. No new infrastructure, model flags or dependencies.
Security impact: none (documentation and read-only local inventory). No separate
security review is required. Production correctness review applies if a later
parameter revision is implemented, not to this read-only assessment.

Deliverables: parsed template inventory and table/export differences; annotated
Fortran data flow and analytic thresholds; literature evidence with units and
measurement definitions; proposed sensitivity matrix and revision decision.
