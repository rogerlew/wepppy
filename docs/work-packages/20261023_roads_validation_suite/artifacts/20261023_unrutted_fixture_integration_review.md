# Independent unrutted fixture contract review

Date: 2026-10-23 UTC. Reviewer: integration_contract_review.
Disposition: approved; no unresolved high or medium finding. This is a bounded
validation-fixture amendment, with no production geometry, default, failure-policy
or schema change.

The full-upload failure and separate positive subset answer different acceptance
questions. Keeping both is appropriate: the former tests rejection and unpublished
failure state; the latter tests feasible replacement/controller/accounting
integration. The contract explicitly prohibits iterative exclusions and a claim
that the complete original upload succeeds. It also correctly excludes a pure
design-effect interpretation of watershed differences against the full-upload
additive controls.

## Direct read-only evidence

Inspected `/wc1/runs/ro/roads-validation-oct23-v2-unrutted`:

- `validation-input.geojson` contains 55 features, with exactly one OSUNUM `6`.
- Its prepared `roads-seg-000001` carries OSUNUM `6` and the explicit 30 m,
  10% fill/buffer controls.
- Retained manifest under history `b8aba5dc0bed4ef3831a6a52192170d2` contains
  exactly two failed rows for this segment: Topaz 271/272, WEPP 61/62, both
  `failed_non_positive_top_ofe`. It also contains two completed rows; those
  partial successes do not establish a current full run.
- The log records two failed segments and the explicit run exception.
  `wepp/roads/output/roads.current.json` is absent.
- The transformed negative input has SHA-256
  `969675b96baed55abd88f11d9079a65ca95bbe8d771031c3347baaadaab4cb1a`.
  This is the experiment input hash, not a claim about the untouched source upload.

## Positive-fixture implementation conditions

Use a fresh independent clone and remove exactly the identified source feature.
Bind the original upload and excluded feature bytes/identity; reject an absent,
ambiguous or different feature instead of broadening selection. Record 55 source
features and 54 selected input features for this upload, followed by actual
prepared, completed and skipped counts/reasons. Preserve the negative attempt.

The positive result still requires fresh native execution, a validated current
receipt, nonzero unrutted replacement contributors, accounting reconciliation and
unchanged source/baseline artifacts. Every published table or statement describing
the project comparison must make the unrutted subset qualification visible.
Completion of this review is not evidence that the positive fixture already ran.

## Reviewed bindings

| Document | SHA-256 |
| --- | --- |
| roads-validation-suite-contract.md | `4cc8731d2ec5301596be19544226049100ea28978bb44cc7c8588fbf2f21231c` |
| 20261023_unrutted_fixture_decision.md | `71970a183536b60adf7420c774a0d54a982e2b91c247c7cd25ad0260e0757138` |
