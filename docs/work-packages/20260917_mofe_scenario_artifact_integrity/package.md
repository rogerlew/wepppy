# MOFE scenario artifact integrity and Abdisa run repair

**Status**: Open (2026-09-17)
**Timezone**: UTC

**Deployment authority update (2026-09-18)**: Roger explicitly requested deployment
on wepp1, wepp2, and wepp3. That request supersedes the earlier operator-only
deployment restriction below for this ordered canonical rollout. Production
scenario repair remains separate from this deployment turn.

## Overview

Rithet Creek scenario runs persisted the requested burn or thinning state in
`landuse.nodb`, but generated multiple-overland-flow-element (MOFE) management
files did not consistently contain that state. As a result, distinct scenarios
could execute with byte-identical WEPP management inputs and produce identical
response summaries. This package corrects the three confirmed generation paths,
proves the result on an actual cloned project on Forest, and only then prepares
the manual repair of all eight Abdisa runs after the operator deploys the accepted
revision to WEPPcloud.

## Objectives

- Make SBS-derived MOFE assignments consume the classified severity codes that
  `SoilBurnSeverityMap.build_lcgrid()` actually returns.
- Make the class-to-class landuse mapping operation regenerate MOFE management
  files from its updated segment assignments before reporting success.
- Propagate an existing management summary's explicit canopy-cover override into
  MOFE management synthesis while preserving the existing RAP-specific override.
  Invoke the existing writer from the public canopy edit and retain MOFE canopy
  overrides during summary rebuilding, so the complete thinning workflow works.
- Add regressions that reproduce the real contracts instead of test doubles that
  return raw SBS pixels where production returns classified codes.
- Validate the candidate on Forest with an actual project clone and content-level
  input/output evidence; job completion or NoDb state alone is not acceptance.
- After the operator deploys the accepted revision, manually rebuild and rerun
  every named Abdisa project on wepp1 and retain before/after evidence.

## Scope

### Included

- Canonical contract coverage for SBS classification, global landuse remapping,
  explicit canopy overrides, generated MOFE files, and downstream WEPP inputs.
- Minimal fixes in `wepppy/nodb/core/landuse.py` and
  `wepppy/rq/project_rq.py`, with focused NoDb/RQ tests and affected docs.
- Local focused and broad regression validation.
- Forest deployment of the candidate revision through the canonical deployment
  path and acceptance on a real Rithet Creek clone or canonical restored copy.
- Content inspection of `landuse/hill_*.mofe.man`, `wepp/runs/*.man`, relevant
  soil inputs, scenario outputs, and the hillslope response summary.
- An operator-gated production repair of these eight run IDs:
  `ventilated-gag`, `equestrian-bonheur`, `tactful-aging`,
  `incorporate-cerebrum`, `choice-feminist`, `neoliberal-dictate`,
  `acetic-surprise`, and `uncrowned-bolt`.

### Explicitly Out of Scope

- Deploying the candidate to wepp1, wepp2, or wepp3. The requesting operator
  owns that deployment and must explicitly confirm it is complete.
- Mutating any Abdisa production run before that deployment confirmation.
- Changing disturbed lookup values, treatment formulas, severity thresholds,
  cover percentages selected by the user, soil parameterization, or RAP formulas.
- Adding queues, services, datastores, daemons, dependencies, privileges,
  protocols, deployment topology, or silent fallback behavior.
- Treating output inequality by itself as proof. Generated inputs must encode the
  requested scenarios; any legitimately equal model results must be explained
  from those verified inputs rather than forced to differ.

## Complexity Budget

- **Existing mechanisms reused**: `Landuse._build_multiple_ofe`, existing
  management summaries, `modify_landuse_mapping_rq`, current NoDb locking and
  cache guards, canonical RQ status, project clone/archive workflows, WEPP build
  and run jobs, `wctl`, and the established production deployment script.
- **New mechanisms permitted**: regression fixtures and retained validation
  manifests/scripts under this package only; no new runtime mechanism.
- **Simplest plausible change tested first**: consume the classified SBS code,
  rebuild from the already-updated MOFE assignment dictionary, and initialize
  MOFE canopy synthesis from the existing summary override while leaving RAP's
  segment override precedence unchanged.
- **Real acceptance condition**: a Forest-hosted actual project produces
  scenario-specific management inputs that match persisted intent, those inputs
  propagate into `wepp/runs`, and completed WEPP outputs are regenerated and
  compared across baseline, fire, SBS, prescribed-burn, and thinning scenarios.
- **Evidence required before escalation**: retained failing tests or Forest
  artifacts showing that the bounded changes cannot satisfy that condition.
- **Explicitly prohibited expansion**: new infrastructure, changed scientific
  parameter values, queue topology, authorization, run schemas, or hidden repair
  storage.
- **Rejected design**: the operator rejected an unapproved attempt store,
  publication ledger, recovery/retention protocol, event-deduplication change,
  and full-workflow transaction fence as disproportionate and fragile. They are
  not part of this package.

## Implementation Fidelity and Evidence

- **Fidelity target**: faithful correction of existing scenario intent.
- **Authoritative source paths**: `wepppy/nodb/core/landuse.py`,
  `wepppy/nodb/mods/baer/sbs_map.py`, `wepppy/rq/project_rq.py`, and the canonical
  contracts ratified by this package.
- **Cutover proof required**: Forest containers run the exact candidate revision,
  and an actual cloned/restored project exercises the public scenario workflows.
- **Acceptance evidence type**: both generated-output and direct unmocked
  boundary evidence; fixture-only evidence cannot close the package.

Generated-artifact acceptance follows
`docs/standards/generated-artifact-validation-standard.md`. The highest supported
status is currently `environment validated`: implementation `f4152ac69` passed
focused and full-suite tests. Forest's eight real scenarios, parsed generated
inputs, fresh outputs, browser/download, failure/retry, and archive/restore all
pass, with final independent correctness and QA PASS. Production deployment,
affected-run repair, and incident resolution remain separate future gates.

## Stakeholders

- **Primary**: Roger as WEPPcloud operator; Abdisa as the affected project owner.
- **Reviewers**: independent correctness reviewer and independent QA reviewer.
- **Security Reviewer**: not required unless implementation expands the current
  authorized RQ/filesystem boundary.
- **Informed**: WEPPcloud maintainers responsible for Forest and wepp1 operations.

## Success Criteria

- [x] A reviewed canonical contract checkpoint is committed as a standalone
      ancestor before implementation edits.
- [x] A real `SoilBurnSeverityMap` regression fails on the current double
      classification and passes after the correction.
- [x] The class-to-class RQ operation regenerates MOFE files from the updated
      assignments and fails explicitly without reporting completion if generation
      fails.
- [x] Explicit 30% and 50% canopy overrides are visible as 0.30 and 0.50 in the
      generated MOFE and prepared WEPP management inputs; existing RAP behavior
      remains covered and unchanged.
- [x] Focused tests, related NoDb/RQ tests, broad exception enforcement, and
      `wctl run-pytest tests --maxfail=1` pass.
- [x] The exact candidate revision is deployed to Forest and an actual project
      exercises all eight scenario roles with retained content hashes, parsed
      management values, job IDs, and output comparisons.
- [x] Forest evidence proves the prior false-positive condition is absent: a
      successful job and correct NoDb state are accompanied by correct generated
      `landuse` and `wepp/runs` artifacts.
- [ ] The operator explicitly confirms the accepted revision has been deployed to
      WEPPcloud before any production run mutation begins.
- [ ] All eight Abdisa runs are processed on wepp1, with pre-repair artifacts
      retained, exact job IDs recorded, generated inputs verified, WEPP rerun,
      and a refreshed hillslope response summary compared with the report.
- [x] Independent correctness and QA reviews pass with no unresolved high or
      medium findings; package, tracker, contracts, and operator documentation are
      current.

## Parameterization ADR Gate

- **Parameterization change present**: no.
- **ADR required**: no.
- **ADR links**: not applicable.
- **Decision provenance captured**: yes; the user requested correction of stored
  scenario propagation and explicitly reserved production deployment to himself.

The fix propagates existing classified values, selected management classes, and
stored cover overrides. If implementation would change formulas, thresholds,
defaults, scientific lookup values, or RAP precedence, stop and add the required
ADR before proceeding.

## Dependencies

### Prerequisites

- Contract-first checkpoint and independent reviews for the UI-coupled NoDb/RQ
  behavior.
- A clean candidate revision that can be deployed through the installed Forest
  production-compose preset.
- A supported clone or archive/restore of the actual Rithet Creek project on
  Forest, without modifying its production source.

### Blocks

- Production repair is blocked until Forest acceptance passes and Roger confirms
  his WEPPcloud deployment is complete.
- Package closure is blocked until the production repair ledger covers all eight
  named runs and the refreshed summary has been checked.

## Related Packages

- **Prior incomplete fix**:
  [`20260907_mofe_mapping_lookup`](../20260907_mofe_mapping_lookup/package.md)
  corrected mapping namespace lookup but did not perform a complete live
  landuse/WEPP replay.
- **Related selected-hillslope work**:
  [`20260911_modify_landuse_mofe`](../20260911_modify_landuse_mofe/package.md)
  covers a different selected-hillslope operation and does not govern global
  class-to-class mapping.
- **Current package**: owns the recurrence, full generated-artifact correction,
  Forest acceptance, and operator-gated Abdisa repair.

## Timeline Estimate

- **Expected duration**: multi-stage; implementation and Forest acceptance first,
  then operator deployment and production repair.
- **Complexity**: medium.
- **Risk level**: high because the final phase mutates production scientific runs.

## Security Impact and Review Gate

- **Security impact triage**: low.
- **Dedicated security review required**: no.
- **Triage rationale**: the change stays within existing authorized NoDb, RQ, and
  run-directory writers. It adds no endpoint, payload, auth rule, queue edge,
  subprocess type, egress, secret, or path authority. Reassess as high if the
  implementation expands any of those surfaces.
- **Security review artifact**: not applicable under the current scope.

## Hardening and Callus Softening

- **Failure signatures**: distinct intended scenarios have correct-looking NoDb
  state but byte-identical generated MOFE management manifests; thinning runs
  with 0.30 and 0.50 stored overrides both generate 0.40 canopy; a completed
  clone job can reproduce baseline management bytes.
- **Related prior hardening efforts**: the two packages listed above and
  `docs/standards/hardening-lifecycle-standard.md`.
- **Health signals**: NoDb, `landuse/hill_*.mofe.man`, prepared `wepp/runs/*.man`,
  and scenario metadata agree; the incident regressions remain green; real
  Forest and repaired production scenarios retain expected input distinctions.
- **Danger signals**: another green job with baseline-equivalent artifacts,
  tests that mock the failing classification/writer boundary, mixed-generation
  files after a failed rebuild, changed scientific values, or a production repair
  attempted before deployment confirmation.
- **Observation window**: recurrence-triggered after the bounded Forest and
  production pre/post snapshots; any recurrence opens a new incident package.
- **Temporary calluses introduced**: none planned.
- **Callus softening hypothesis**: not applicable.

## References

- `artifacts/20260917_incident_evidence.md` - confirmed production and historical
  clone evidence.
- `artifacts/20260917_contract_decision.md` - proposed contract checkpoint.
- `artifacts/20260917_forest_acceptance.md` - hard-gated live acceptance record.
- `artifacts/20260917_wepp1_repair_ledger.md` - post-deployment production ledger.
- `docs/schemas/disturbed-mofe-mapping-contract.md` - current severity remap
  contract.
- `docs/schemas/landuse-modification-contract.md` - separate selected-hillslope
  behavior.
- `docs/standards/artifact-observability-standard.md` - retained artifact gate.
- `docs/standards/generated-artifact-validation-standard.md` - evidence chain and
  completion-claim authority promoted from this incident's broader lesson.
- `/tmp/hillslope_response_summary.csv` - reporter-supplied comparison input;
  SHA-256 is recorded in the incident artifact.

## Deliverables

- Canonical contract and reviewed standalone checkpoint.
- Minimal source correction and focused regression coverage.
- Local validation, correctness, QA, and Forest acceptance artifacts.
- Updated operator/developer documentation for the affected workflow.
- Completed production repair ledger and refreshed hillslope response comparison.

## Follow-up Work

No follow-up is currently authorized. Discoveries outside the three confirmed
defects must be recorded and separately scoped instead of expanding this package.
