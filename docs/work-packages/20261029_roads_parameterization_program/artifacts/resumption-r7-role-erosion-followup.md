# Additional check: role-specific erosion anchors

The final feasibility check reviewed the revision-2 experiment that conditioned
fill/buffer erosion coefficients on legacy role priors while preserving generated
hydraulic profiles, to assess whether current evidence justifies repeating it.

The frozen 333-call declaration changed only `ki`, `kr` and `shcrit` in fill,
buffer or both, retaining generated horizons, the 200 mm boundary, restrictions,
road settings and hydraulics, and requiring byte-identical WAT. All 333 calls
completed and passed their then-declared physical checks. Of 44 selected small
exceedances, fill/both recovered one and buffer recovered none; each lane lost
the one selected small-load passing control. The best combined recovery was
10 of 91 original misses, with a control regression. Ledger v3 rejected the
standalone candidate.

This is historical revision-2 evidence, not a renewed r7 efficacy test. The
current fixed-input full840 replay preserves all r4 magnitude classifications,
and the new retention trial supplies no new source or causal evidence for
retrying those erosion priors. A newly discriminating observation could justify
a bounded reconsideration under existing autonomy; this check does not claim
mathematical impossibility or automatically transfer all old physical validation
to r7. It identifies no presently supported reason to repeat the old sweep.

No model calls, coefficient edits, defaults or acceptance changes occurred.
The [next-mechanism assessment](resumption-r7-next-mechanism-feasibility.md)
remains the current evidence-based next-step recommendation.

Evidence bindings:

- `erosion-ablation-v1-declaration.json` SHA256 `de0a6cebf2f84aa0266a2d52663df214c5cf418741d3fba6f02906e6eeca916c`.
- `erosion-ablation-v1-summary.json` SHA256 `6636c540862bae3481a7c70087056e9c79656b802d3139f52928d8f039444e1b`.
- `candidate-ledger-v3.json` SHA256 `b6617ea2f39fc9d1a6e3067ceaf6738969291471f3857ee3637f189a0dc415bc`.
