# WP12D Amendment 2 Advisory Governance Review

**Amendment**: `PC-24/WP12D-20260827-2`
**Review status**: superseded by unratified amendment 3; chronology only
**Review type**: advisory, pre-ratification

Initiative branch: feature/project-owned-config
Canonical branch: master
Promotion policy: merge only at the roadmap promotion gate

## Initial Verdict

`NOT READY`.

## Findings and Disposition

- **High - canonical RQ contract was missing**: closed by adding
  `rq-engine-agent-api-contract.md` to the checkpoint and requiring exact
  run-discovery parity while preserving the generic RQ envelope.
- **High - project-local and query-override states were unresolved**: closed
  with an explicit local precedence/compatibility matrix and pre-publication
  rejection of every locale-bearing creation override.
- **High - global locale-property scope was too broad**: closed by making
  `NoDbBase.locales` an explicit non-change and enumerating the exact landuse,
  soils, and climate core consumers.
- **Medium - the inventory was not closed**: closed with all 128 filenames,
  current literal state, proposed effective composition, source,
  classification, and authority mode.
- **Medium - rollback semantics were contradictory**: closed with atomic
  restoration of exact revision `187a856d47e522cfd7ed489a53d06007ed8e1bf7`
  and that revision's matching pre-WP12D configs.

## Fresh Verdict

The first fresh re-review remained `NOT READY`:

- **High - checkpoint security sequence was incomplete**: closed by requiring
  a binding dedicated security review of the ratified canonical diff before
  checkpoint commit, plus a fresh final security review of implementation.
- **Medium - absent and explicit-empty locale were conflated once**: closed by
  changing the compatibility statement to absent only; explicit empty remains
  invalid.
- **Medium - established-Interface non-submission contradicted Builder
  creation**: closed by scoping the non-submission rule to established links
  and forms and preserving Builder's validated locale payload/provenance.
- **Medium - the generic RQ envelope contract was omitted**: closed by listing
  `rq-response-contract.md` as unchanged applicable authority and requiring
  additive route-specific semantics. The RQ controller-state contract is also
  explicitly included because schemas, operation documents, pipeline, and
  readiness change.

Independent post-fix verdict: `READY`; no remaining High/Medium advisory
findings. Governance re-confirmed `READY` after the compatibility refinement
that excludes flattened no-capability/schema-v1 projects from new locale
validation and makes Turkey classification-only. This advisory review cannot
satisfy the later binding reviews of the ratified canonical checkpoint.

The operator subsequently added explicit capability-authority refresh. That
material delta requires fresh amendment-3 advisory review; this verdict grants
no approval to the current proposal.
