# Topanga Peak-Flow Census Preparation Disposition

## Disposition

**GO** to create the separately dated
`20260809_peakflow_topanga_census_execution` work package. This disposition
does not authorize execution from the preparation package, and the execution
package has not been scaffolded here.

The frozen canonical plan is
`artifacts/topanga-trial-plan.json`. Its content-derived plan ID is
`b575fde4a28cf85f1d28e0dfff305472b5419fd9b3639d39dc437600617080de`
and its file SHA-256 is
`32e6f5e99a77747fcdd93388302f2a5ffb496a87b764ac4505e09691955db756`.
The study-manifest SHA-256 is
`40eb640c514e1715f83a79dc31ecd8fb2c93dd55252ee48823d87986a3f47c80`.

## Frozen Denominators

The plan contains 1,120 requested records: 560 Ksat and 560 paired-cover
records. All 560 Ksat records are eligible. Of the cover records, 528 are
eligible and 32 are excluded because both cover directions cannot be realized
without clipping. The resulting execution denominator is 1,088 eligible
trials: 546 burned and 542 undisturbed. Every exclusion is retained in the
plan with reason `paired_cover_direction_would_clip`.

The Phase 2A scaling projection is 4,527.492835592012 sequential seconds and
16,089,950,152 retained bytes for the eligible local hillslope trials. The
future external evidence locator is
`/home/workdir/peakflow-topanga-census-evidence/b575fde4a28cf85f1d28e0dfff305472b5419fd9b3639d39dc437600617080de`.
It contains no files at preparation closeout.

## Gate Evidence

The reusable engine reproduced all accepted immutable pilot denominators: 64
complete terminals, 14,157 outer event pairs, 30 baseline-only rows, 25
mutant-only rows, 697 candidate rows, and 61 candidate trials. One explicitly
selected burned h106 Ksat-minus trial was executed under the separate
preparation-validation root; its trace and hillslope-pass hashes exactly match
Phase 2A. Synthetic non-Topanga, noncontiguous planning and content-ID,
clipping, symlink, path-root, retry-binding, and outer-join tests pass.

Security, code, and QA reviews pass with no unresolved medium or high finding.
Canonical container pytest is blocked by the known full `/tmp` condition, with
the exact failure recorded in `artifacts/20260809_qa_review.md`; the local
focused suites pass 9 new tests and 5 existing pilot tests. Documentation lint,
schema validation, Python compilation, broad-exception review, and diff checks
pass.

## Execution-Package Handoff Contract

The next agent must create the separately dated execution package before any
full-census run. It must consume the frozen plan bytes unchanged, verify the
plan ID and file hash above, and require an explicit selection containing the
1,088 eligible trial IDs. It must not recalculate eligibility after outcomes
exist or include any excluded trial.

The execution package must verify the pinned observer SHA-256
`2ec15778df957f909da383df9e3e0c9b516688d367c11f0109c6012387c0731f`,
both frozen input-tree hashes, terminal schema bindings, and evidence-root
containment before launch. It must retain stopped or failed terminals, preserve
prior attempts on retry, outer-join events without replacing absence by zero,
and use the unchanged screening floors and mutation magnitudes. Watershed
routing, channel outputs, canopy, and LAI remain out of scope.

Any proposed manifest, executable, input-authority, eligibility, mutation, or
screening change invalidates this GO. Such a change requires a new preparation
decision, a new plan ID, and a new disposition before execution.
