# Production M1 contract checkpoint

Starting implementation revision: `304572530`. Implementation conformance pending.
Owner authorization: the instruction “execute the work-package” follows review
and explicit correction of UI labels, preflight, date removal, distribution Auto
and uploaded-map summary. It authorizes the package's required checkpoint commit
and implementation, not pushing or deployment. Preserve unrelated quality reports.

Current canonical delta: production M1 workflow `docs/production_m1.md#execution-contract-2026-09-10`,
UI control contract, ADR-0063, module specification and feature-registry
specification. Shared NoDb persistence/cache, RQ response/config/access, CSRF,
controller and locale authority contracts remain unchanged. New feature metadata
is specified before adding its YAML/runtime registration.

Exact behavior and engineering choices are in the execution contract; the static
`ui_preview.html` represents six states using the approved layout and upload table.
`auto_scale_evaluation.json` records three real scaled products, normalized
counterparts and five analytical cases. It demonstrates the proposed distribution
rule on these cases, not universal encoding accuracy.

Compatibility plan: additive optional NoDb and artifact subtree, new run-scoped
routes/control. No legacy debris_flow migration, existing backend signature or
scientific formula changes, and no implicit upstream builds. No generated WEPP
run input mutations; new artifacts are normalized dNBR, predictor and result
bundles whose hashes/values must be checked end-to-end. Unit preferences affect
presentation only. Unknown image dates remain permitted; source association is
checked where metadata exists and described as user responsibility otherwise.

Security impact: high (upload decoder, authenticated execution, persistence and
file publication). Both valid-state reachability and hostile-boundary tests are
mandatory: real multipart byte limits, bounded decoder/VRT, candidate ownership,
actual NoDb lock/cache writes, enqueue ambiguity, stale publication, readonly and
config mismatch, hidden staging and fixed output access. Dedicated final security
review and production-equivalent browser/worker evidence remain release gates.

Discrepancy classification: intended additive enhancement. Prior metadata-only
Auto proposal is superseded by owner distribution request. No historical packages
are amended. Reviews and disposition are recorded before the ancestor commit;
implementation files have not been edited.

Both independent read-only reviews approve checkpoint/implementation; all high
and medium findings were incorporated and confirmed closed. Dedicated review
artifacts record the dispositions. Runtime evidence remains pending.
