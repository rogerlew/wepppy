# Peridot Documentation Repositioning and Adoption Visibility ExecPlan

This ExecPlan is a living document. The sections `Progress`, `Surprises & Discoveries`, `Decision Log`, and `Outcomes & Retrospective` must be kept up to date as work proceeds.

This plan must be maintained in accordance with `docs/prompt_templates/codex_exec_plans.md`.

## Purpose / Big Picture

After this package is executed, Peridot documentation will clearly present Peridot as a production-critical watershed abstraction engine in the WEPPpy stack, not as an incidental utility. A new contributor or operator should be able to read the Peridot docs and quickly understand replacement scope, output contracts, migration boundaries, operational failure signatures, and how benchmark claims are supported.

The visible result is a documentation set that improves adoption confidence and reduces ambiguity for integrators, operators, and reviewers. Required framing is "category shift, not modernization": explicit graph abstraction replacing implicit legacy discretization mental models.

## Progress

- [x] (2026-04-26 21:20 UTC) Work-package scaffold created (`package.md`, `tracker.md`, `prompts/*`, `notes/`, `artifacts/`).
- [x] (2026-04-26 21:21 UTC) Package brief authored with scope, success criteria, and cross-repo references.
- [x] (2026-04-26 21:23 UTC) Active ExecPlan authored in `prompts/active/`.
- [x] (2026-04-26 21:27 UTC) Incorporated user directional guidance for GPT-5.5 into package/plan constraints and added guidance note artifact.
- [x] (2026-04-26 21:42 UTC) Audited Peridot source anchors for output paths, schema fields, CLI flags, representative-flowpath behavior, and current error propagation boundaries.
- [x] (2026-04-26 21:44 UTC) Executed Milestone 1 README restructuring in `/home/workdir/peridot` with why-it-matters, category-shift framing, legacy/current comparison, replacement boundaries, canonical links, and communication kit.
- [x] (2026-04-26 21:44 UTC) Executed Milestones 2-5 by adding Peridot output contract, benchmark discipline, migration guide, and operations runbook docs.
- [x] (2026-04-26 21:45 UTC) Executed Milestone 6 by aligning WEPPpy-facing references to canonical Peridot docs and softening unqualified speedup claims.
- [x] (2026-04-26 21:45 UTC) Executed Milestone 7 artifact setup by adding claim provenance and validation summary artifacts.
- [x] (2026-04-26 21:49 UTC) Ran requested doc validation and updated final validation artifact with command results.
- [x] (2026-04-26 21:50 UTC) Ran additional changed-WEPPpy-doc lint and removed a dead `API_REFERENCE.md` link from touched `wepppy/README.md`.
- [x] (2026-04-26 22:36 UTC) Addressed post-implementation review findings for sub-field input contract, historical culvert CSV wording, and README `discha.vrt` coverage.

## Surprises & Discoveries

- Observation: Package scaffold and tracker were present, but the active ExecPlan file had not yet been created during initial package setup.
  Evidence: `find docs/work-packages/20260426_peridot_documentation_repositioning -maxdepth 3 -type f` initially returned only `.gitkeep`, `package.md`, and `tracker.md` before the planning update.

- Observation: Root tracker did not yet include the new package entry during initial package setup.
  Evidence: `rg -n "20260426_peridot_documentation_repositioning|Peridot Documentation Repositioning" PROJECT_TRACKER.md` returned no matches before the planning update.

- Observation: Messaging risk is deeper than "insufficient prominence"; field framing defaults to legacy TOPAZ/TOP2WEPP mental models, causing Peridot advances to be interpreted as incremental.
  Evidence: User directional guidance explicitly requested reclassification as a category shift and required communication kit (claim + figure + metrics).

- Observation: The old Peridot README advertised `channels.csv`, `hillslopes.csv`, and `flowpaths.csv` as watershed CLI outputs, but current watershed abstraction paths write Parquet tables and generated manifests directly.
  Evidence: `src/watershed_abstraction/watershed_abstraction.rs` and `src/wbt/wbt_watershed_abstraction.rs` call Parquet writers and `write_watershed_readme`; no watershed CSV writer is called in those CLI paths.

- Observation: Peridot watershed CLI entrypoints currently discard the underlying abstraction `Result`, so some write-stage errors may not be visible in process exit status.
  Evidence: `src/bin/abstract_watershed.rs` and `src/bin/wbt_abstract_watershed.rs` call `let _ = abstract_watershed(...)` / `let _ = wbt_abstract_watershed(...)` before returning `Ok(())`.

- Observation: `field_flowpaths.csv` currently emits two headers named `topaz_id`.
  Evidence: `src/watershed_abstraction/flowpath_collection.rs::write_field_subflows_metadata_to_csv` writes `field_id`, `topaz_id`, `sub_field_id`, `topaz_id`, `fp_id`, and remaining fields.

- Observation: `sub_fields_abstraction` does not read `netw.tsv`, even though the initial contract wording implied it inherited all WBT watershed inputs.
  Evidence: `src/wbt/wbt_sub_fields_abstraction.rs` reads the WBT raster stack and field raster; `src/wbt/wbt_watershed_abstraction.rs` is the command that reads `dem/wbt/netw.tsv`.

## Decision Log

- Decision: Track this as a WEPPpy work-package while explicitly targeting implementation edits in `/home/workdir/peridot`.
  Rationale: Planning/discovery needs to stay in WEPPpy's governance surface, while Peridot documentation remains the source of truth for Peridot behavior.
  Date/Author: 2026-04-26 / Codex.

- Decision: Prioritize docs that prove operational relevance (`README`, contract, migration, operations, benchmark method) before deep internal architecture narratives.
  Rationale: Current risk is under-positioning and ambiguous adoption messaging, not a missing internal implementation walkthrough.
  Date/Author: 2026-04-26 / Codex.

- Decision: Encode a hard narrative constraint that Peridot is documented as a graph-based abstraction-layer shift rather than a "modernized replacement."
  Rationale: Without explicit mental-model reset language, readers map improvements to legacy equivalence and miss methodological impact.
  Date/Author: 2026-04-26 / Codex.

- Decision: Document the current Parquet-first watershed CLI contract instead of reintroducing CSV outputs.
  Rationale: The package is docs-first and the source audit confirmed current CLI behavior. Runtime changes would need a separate package with downstream compatibility validation.
  Date/Author: 2026-04-26 / Codex.

- Decision: Treat CLI error propagation hardening and sub-field duplicate-header cleanup as follow-up runtime/schema packages.
  Rationale: Both issues are real contract risks, but changing exit-code semantics or CSV schema under a documentation-only package would exceed approved scope.
  Date/Author: 2026-04-26 / Codex.

- Decision: Treat completed culvert integration plan `flowpaths.csv` wording as historical context instead of rewriting old package history wholesale.
  Rationale: The file is a completed implementation plan. Short historical-contract notes preserve what was true for the package narrative while pointing current readers to the canonical Peridot Parquet-first contract.
  Date/Author: 2026-04-26 / Codex.

## Outcomes & Retrospective

Implementation and validation are complete. Peridot now has a README front section that explains why Peridot matters, explicitly compares implicit raster legacy abstraction with explicit graph abstraction, states replacement boundaries, links to canonical docs, and includes the requested communication kit.

The Peridot docs set now includes `docs/contracts/watershed-output-contract.md`, `docs/benchmarks.md`, `docs/migration/prepwepp-to-peridot.md`, and `docs/operations.md`. WEPPpy references that previously made scattered or unqualified Peridot claims now point to canonical Peridot docs and treat performance claims as evidence-bound.

The requested WEPPpy doc-lint passed with `7 files validated, 0 errors, 0 warnings`. Peridot has no repository-local Markdown/doc tooling, so manual path and local-link validation was performed and passed. An additional lint pass over the changed WEPPpy docs also passed after removing a pre-existing dead `API_REFERENCE.md` link from the touched `wepppy/README.md`. The main lesson is that repositioning exposed contract drift. The safest docs-first action was to correct the documentation surface, record the mismatch, and recommend runtime/schema follow-ups rather than silently changing behavior.

Post-implementation review found three documentation issues. They were remediated without runtime changes: sub-field inputs now exclude `netw.tsv`, README representative-flowpath inputs now include `discha.vrt`, and the historical culvert plan now maps old `flowpaths.csv` language to the current Peridot output contract.

## Context and Orientation

This package coordinates documentation work across two repositories:

- Planning and tracking artifacts live in `/workdir/wepppy/docs/work-packages/20260426_peridot_documentation_repositioning/`.
- Peridot docs implementation targets `/home/workdir/peridot`.

Key Peridot inputs:

- `/home/workdir/peridot/README.md` is the primary user entrypoint and now contains the category-shift framing and canonical links.
- `/home/workdir/peridot/docs/contracts/watershed-output-contract.md` is the canonical direct Peridot output contract.
- `/home/workdir/peridot/docs/benchmarks.md` defines claim discipline and benchmark methodology.
- `/home/workdir/peridot/docs/migration/prepwepp-to-peridot.md` defines migration scope and intentional differences.
- `/home/workdir/peridot/docs/operations.md` defines operational commands, validation, and failure signatures.
- `/home/workdir/peridot/src/watershed_abstraction/watershed_manifest.rs`, `/home/workdir/peridot/src/bin/*.rs`, `/home/workdir/peridot/src/watershed_abstraction/watershed_abstraction.rs`, `/home/workdir/peridot/src/wbt/wbt_watershed_abstraction.rs`, and `/home/workdir/peridot/src/watershed_abstraction/flowpath_collection.rs` are the behavior/contract sources used for evidence.

Key WEPPpy integration context:

- `/workdir/wepppy/wepppy/README.md` now links to canonical Peridot contract and benchmark docs.
- `/workdir/wepppy/docs/projects/i-crews/st_joe/procurement-request.md` now treats historical Peridot speedups as workload-specific benchmark claims.
- `/workdir/wepppy/docs/dev-notes/data_tables_standardization.spec.md`, `/workdir/wepppy/docs/dev-notes/query_engine.spec.md`, and `/workdir/wepppy/docs/schemas/output-scope-contract.md` now point to the canonical Peridot output contract where appropriate.

Terms used in this plan:

- "Output contract" means the documented set of files, tables, columns, and flags that downstream systems rely on.
- "Replacement scope" means the specific areas where Peridot supersedes prepwepp/topaz abstraction behavior, and explicit non-goals where legacy expectations still differ.
- "Category shift" means moving from implicit raster segmentation workflow assumptions to explicit graph topology as the primary abstraction surface.
- "Claim discipline" means distinguishing `confirmed` (direct evidence), `inference` (reasoned from architecture), and `hypothesis` (directional but unverified) statements in package artifacts.

## Plan of Work

Milestone 1 rewrote the top of Peridot `README.md` so the first screen answers three questions: why this project matters to WEPPpy operations, what it replaces, and where canonical docs live for contracts and operations. This milestone included a concise category-shift statement and a legacy-vs-current paradigm contrast.

Milestone 2 added a watershed output contract document in Peridot docs. It defines output artifacts, table fields, CLI/runtime flags affecting outputs, known edge conditions, and current error-boundary risks.

Milestone 3 added a benchmarks method doc that distinguishes measured facts from hypotheses. It includes dataset assumptions, hardware context, command templates, and evidence-label rules.

Milestone 4 added a migration guide from prepwepp/topaz abstraction expectations to Peridot behavior. It explicitly calls out parity areas, intentional differences, and operational impact on WEPPpy users.

Milestone 5 added operations guidance: failure signatures, troubleshooting flow, expected outputs, and escalation boundaries.

Milestone 6 aligned WEPPpy-facing references so cross-repo links point to canonical Peridot docs rather than ad hoc statements.

Milestone 7 added the minimal communication kit needed for legibility to legacy audiences: one clean claim statement, one comparison-figure specification, and three core metric definitions.

## Concrete Steps

Completed source audit commands included:

    cd /home/workdir/peridot
    rg -n "PATHS|channels.parquet|hillslopes.parquet|flowpaths.parquet|write_watershed_readme|skip_flowpaths|representative_flowpath" src/watershed_abstraction src/wbt -g '*.rs'
    sed -n '1,180p' src/bin/sub_fields_abstraction.rs
    sed -n '260,500p' src/watershed_abstraction/watershed_manifest.rs

Completed WEPPpy reference audit command included:

    cd /workdir/wepppy
    rg -n "Peridot|peridot|TOPAZ|TOP2WEPP|prepwepp|weppcloud-wbt" wepppy/README.md docs -g '*.md'

Final validation command was run:

    cd /workdir/wepppy
    wctl doc-lint --path PROJECT_TRACKER.md --path docs/work-packages/20260426_peridot_documentation_repositioning

Peridot has no repository-local markdown/doc tooling beyond Rust build/test tooling, so validation uses manual path/link checks recorded in the validation artifact.

Observed validation output:

    ✅ 7 files validated, 0 errors, 0 warnings

## Validation and Acceptance

The package is accepted when all of the following are true:

- Peridot README front matter explicitly states production role and replacement relevance in WEPPpy.
- Peridot README includes explicit legacy-vs-current paradigm framing.
- Canonical docs exist and are linked: contract, benchmarks method, migration guide, operations/troubleshooting.
- Contract claims are traceable to Peridot code or observed artifacts.
- WEPPpy docs that describe Peridot link to canonical Peridot docs.
- Documentation set includes the communication kit.
- High-impact messaging claims are trace-labeled in artifacts as `confirmed`, `inference`, or `hypothesis` where ambiguity exists.
- Work-package tracker and artifacts record what was changed, why, and what evidence supports the claims.
- Markdown lint for touched WEPPpy package docs and root tracker passes.

## Idempotence and Recovery

The plan is documentation-first and additive. Re-running milestones is safe because files are updated in place and canonical links are stable. If a milestone partially lands, recover by finishing README and docs links before expanding narrative depth, keeping unresolved behavior claims clearly marked as known gaps with follow-up items, and re-running doc lint after each edit batch.

No destructive migrations were performed in this package.

## Artifacts and Notes

Execution evidence is captured in:

- `docs/work-packages/20260426_peridot_documentation_repositioning/artifacts/2026-04-26_doc_claim_provenance.md`
- `docs/work-packages/20260426_peridot_documentation_repositioning/artifacts/2026-04-26_validation_summary.md`

The provenance artifact records `confirmed`, `inference`, and `hypothesis` labels for high-impact claims. The validation artifact records doc-lint, Peridot manual path/link validation, and any residual gaps.

## Interfaces and Dependencies

Primary interfaces touched in this package are documentation interfaces:

- Peridot README and docs hierarchy as the canonical public contract surface.
- WEPPpy references that point readers/operators to Peridot canonical docs.

No runtime APIs were changed by this plan. Runtime follow-ups identified during execution are CLI error propagation hardening and sub-field CSV header cleanup.

## Revision Notes

- 2026-04-26 / Codex: Initial ExecPlan authored for package startup; includes milestones for cross-repo Peridot docs repositioning and WEPPpy reference alignment.
- 2026-04-26 / Codex: Updated ExecPlan with GPT-5.5 directional guidance constraints (category-shift framing, communication kit, claim discipline).
- 2026-04-26 / Codex: Updated ExecPlan after implementation with completed milestones, source-audit discoveries, decisions for docs-only mismatch handling, and closure-oriented validation plan.
- 2026-04-26 / Codex: Updated ExecPlan after validation with passing doc-lint and Peridot manual link/path validation results.
- 2026-04-26 / Codex: Recorded additional changed-doc lint and dead-link cleanup in touched WEPPpy README.
- 2026-04-26 / Codex: Recorded review remediation for sub-field input contract, historical culvert CSV wording, and README `discha.vrt` coverage.
