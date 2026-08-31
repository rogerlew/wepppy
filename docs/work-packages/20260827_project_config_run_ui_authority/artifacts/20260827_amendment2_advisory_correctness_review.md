# WP12D Amendment 2 Advisory Correctness Review

**Amendment**: `PC-24/WP12D-20260827-2`
**Review status**: superseded by unratified amendment 3; chronology only
**Review type**: advisory, pre-ratification

Initiative branch: feature/project-owned-config
Canonical branch: master
Promotion policy: merge only at the roadmap promotion gate

## Initial Verdict

`NOT READY`.

## Findings and Disposition

- **High - semantic config inventory was incomplete**: closed with the
  row-level 128-config inventory, explicit Turkey supported-non-Builder
  identity, and explicit Continental-US disposition for `general.cfg`.
- **High - project-local missing locale contradicted no migration**: closed by
  the non-persisting `['us']` compatibility value for a truly absent option,
  explicit empty/invalid failure, and preservation of explicit local values.
- **High - flattened no-capability and source-kind states were missing**:
  closed by preserving existing no-capability/schema-v1 behavior and applying
  every valid schema-v2/v3 stored graph regardless of manifest source kind.
- **High - RQ discovery was outside parity scope**: closed by adding endpoint
  schemas/defaults/errors, operation documents, pipeline, and readiness plus
  their exact modules and tests.
- **Medium - failure transports were not exact**: closed by specifying 409
  `locale_authority_invalid`, 503 `builder_registry_error` with
  `Retry-After: 5`, diagnostic details/error IDs, and boundary-specific
  envelopes/pages.

## Fresh Verdict

The first fresh re-review remained `NOT READY`:

- **High - blanket locale validation conflicted with flattened compatibility**:
  closed by classifying flattened projects first. No-capability/schema-v1
  projects receive no new locale validation or live-registry consultation;
  absent, empty, unknown, and valid locale fixtures must preserve current
  behavior and every present valid v1 axis.
- **Medium - Turkey's profile record was not exact**: closed with stable ID
  `turkey`, label `Turkey`, runtime token `turkey`, base classification,
  `supported_non_builder`, source revision `WP12D-1`, no overlay metadata, and
  five empty closed dataset axes. Yasin's fixed map inputs remain config-owned
  outside Builder authorization, with exact serialization/catalog-revision and
  reopen evidence required.

Independent post-fix verdict: `READY`; no remaining High/Medium advisory
findings. Residual implementation risk is concentrated in classifying every
flattened project before locale/registry access and assigning Turkey's
`WP12D-1` revision without changing existing profiles' `WP12C-1` identities;
the required direct tests cover both. This advisory review cannot satisfy the
later binding reviews of the ratified canonical checkpoint.

The operator subsequently added explicit capability-authority refresh. That
material delta requires fresh amendment-3 advisory review; this verdict grants
no approval to the current proposal.
