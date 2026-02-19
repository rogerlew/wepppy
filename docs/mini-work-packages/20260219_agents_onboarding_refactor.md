# Mini Work Package: AGENTS Onboarding Refactor For Large-Project Guidance
Status: Implemented
Last Updated: 2026-02-19
Primary Areas: `AGENTS.md`, `CONTRIBUTING_AGENTS.md`, `docs/prompt_templates/agents_authoring_template.md`, nested `**/AGENTS.md`
See also: `ARCHITECTURE.md`, `PROJECT_TRACKER.md`, `docs/work-packages/README.md`, `docs/prompt_templates/AGENTS.md`

## Objective
Refactor onboarding guidance so root agent docs follow a large-project pattern:
1. Keep root `AGENTS.md` compact and directive-heavy (table of contents, not encyclopedia).
2. Keep `CONTRIBUTING_AGENTS.md` as a contributor quickstart, not a second policy source.
3. Route detailed guidance to authoritative docs and nearest nested `AGENTS.md` files.

## Baseline Findings (Pre-Refactor Snapshot)
This section records the initial onboarding state before Phases 1-4 were executed.
1. `AGENTS.md` is currently oversize for onboarding (`1100` lines, `55,761` bytes), which front-loads context and increases instruction scan time.
2. The file mixes distinct concerns: mandatory directives, architecture narrative, setup tutorials, testing playbooks, front-end guidance, markdown tooling manual, and task recipes.
3. A template-style README skeleton appears inline (`AGENTS.md:236`-`AGENTS.md:256`), which is useful reference material but not first-hop onboarding guidance.
4. The repo already has substantial nested AGENTS coverage (23 files discovered), but root content still repeats many subsystem instructions those files can own.
5. `CONTRIBUTING_AGENTS.md` correctly aims to be lightweight, but step 1 currently sends every agent directly into the 1100-line root runbook.

## Refactor Principles
1. Preserve critical directives in root onboarding; relocate explanatory depth.
2. Prefer links to canonical docs over copied prose blocks.
3. Keep onboarding deterministic: clear read order, clear command entry points, clear escalation path.
4. Use progressive disclosure:
   - Root `AGENTS.md`: global guardrails and navigation.
   - `CONTRIBUTING_AGENTS.md`: day-1 contributor flow.
   - Nested `AGENTS.md`: subsystem-local rules.
   - `docs/`: long-form system of record.
5. Make size budgets explicit so docs do not drift back into monoliths.

## Target Document Roles
| Document | Role | Target Size Budget | Notes |
| --- | --- | --- | --- |
| `AGENTS.md` | Global policy + documentation map | 100-160 lines | Must keep mandatory authorship block and repo-wide hard directives. |
| `CONTRIBUTING_AGENTS.md` | Contributor quickstart | 60-120 lines | Should reference root `AGENTS.md`, not duplicate policy text. |
| Nested `**/AGENTS.md` | Local implementation rules | Varies by subsystem | Nearest file owns local behavior and validation commands. |
| `docs/*` | Deep reference and workflows | No strict cap | Holds details moved out of root onboarding docs. |

## Scope
### Included
1. Audit root onboarding sections and classify each section as:
   - Keep in root
   - Move to canonical doc
   - Replace with link-only pointer
2. Rewrite `AGENTS.md` into a concise map with explicit read order and pointers.
3. Rewrite `CONTRIBUTING_AGENTS.md` so it complements (not duplicates) root policy.
4. Add/update cross-links so moved guidance remains discoverable.
5. Validate links, markdown lint, and spelling normalization for touched prose.

### Explicitly Out of Scope
1. Broad rewrites of subsystem docs unless needed to receive moved content.
2. Re-architecting existing nested AGENTS hierarchy.
3. Behavioral code changes, test logic changes, or CI pipeline rewrites.
4. Creating a new global policy model outside current Codex AGENTS loading behavior.

## Content Retention Contract (Must Stay In Root AGENTS)
1. Mandatory authorship directive (verbatim).
2. Core directives (`??`, explicit-failure guidance, no silent fallback wrappers).
3. ExecPlan contract and reference to `docs/prompt_templates/codex_exec_plans.md`.
4. Change scope discipline requirements.
5. High-value repo-wide invariants that are unsafe to bury (for example RQ dependency catalog update trigger).
6. Minimal environment assumptions required for almost every task (`wctl`, docker compose source of truth).

## Content Relocation Matrix (Planned)
| Current Root Section Family | Planned Destination | Root Treatment |
| --- | --- | --- |
| Deep architecture overview and component inventories | `ARCHITECTURE.md` plus focused module docs | Keep 3-6 line summary + pointer |
| NoDb implementation patterns and examples | `wepppy/nodb/AGENTS.md` | Link only from root |
| Detailed testing practices, stubs, markers, smoke setup | `tests/AGENTS.md` | Keep one short "validation entry points" block |
| Front-end/controller details and url_for_run rules | `wepppy/weppcloud/AGENTS.md` and `wepppy/weppcloud/controllers_js/AGENTS.md` | Link only from root |
| Markdown tooling reference and command catalog | `docs/prompt_templates/AGENTS.md` and `tools/README.markdown-tools.md` | Keep brief pointer |
| Long task recipes ("Adding X", "Debugging Y") | subsystem AGENTS/README files | Replace with routing map |

## Implementation Plan

### Phase 0: Baseline + Section Inventory
1. Record baseline metrics for both docs (line count, byte size, heading count).
2. Build a section-by-section keep/move/link matrix for `AGENTS.md`.
3. Identify any orphaned guidance that lacks a canonical destination doc.

Deliverable:
- Inventory table committed inside this mini package (or added as a short appendix in the PR description).

### Phase 0 Execution Notes (Completed 2026-02-19)

#### Baseline Metrics
| File | Lines | Bytes | `##` headings | `###` headings | Notes |
| --- | --- | --- | --- | --- | --- |
| `AGENTS.md` | 1100 | 55,761 | 30 | 64 | Oversize onboarding surface; duplicate `## Further Reading`; includes template placeholder headings. |
| `CONTRIBUTING_AGENTS.md` | 51 | 3,731 | 6 | 0 | Already concise and close to quickstart format. |

Largest top-level sections in `AGENTS.md` by line count:
1. `## Getting Help` (148 lines)
2. `## Testing and Validation` (139 lines)
3. `## Module Organization Best Practices` (119 lines)
4. `## Development Workflow` (103 lines)
5. `## Front-End Development` (96 lines)

#### AGENTS.md Section Inventory (Keep/Move/Link Matrix)
| Section (`AGENTS.md`) | Line Range | Size (Lines) | Phase 0 Decision | Canonical Destination |
| --- | --- | --- | --- | --- |
| `## Authorship` | 4-6 | 3 | Keep in root (verbatim) | Root `AGENTS.md` |
| `## Core Directives` | 7-12 | 6 | Keep in root (tight wording) | Root `AGENTS.md` |
| `## ExecPlans` | 13-28 | 16 | Keep in root (condense wording) | Root `AGENTS.md`; `docs/prompt_templates/codex_exec_plans.md` |
| `## Key Contracts` | 29-31 | 3 | Keep in root | Root `AGENTS.md`; `docs/schemas/rq-response-contract.md` |
| `## RQ Dependency Catalog` | 32-35 | 4 | Keep in root | Root `AGENTS.md`; `wepppy/rq/job-dependencies-catalog.md` |
| `## Repository Overview` | 36-39 | 4 | Keep as short summary + link | `ARCHITECTURE.md` |
| `## Core Architecture Patterns` | 40-69 | 30 | Move out of root; link only | `ARCHITECTURE.md`, `wepppy/nodb/AGENTS.md` |
| `## Key Components` | 70-122 | 53 | Move out of root; link only | `ARCHITECTURE.md`, subsystem READMEs |
| `## Module Organization Best Practices` | 123-241 | 119 | Move out of root; split by domain | `wepppy/nodb/AGENTS.md`, `TYPE_HINTS_SUMMARY.md`, `docs/prompt_templates/readme_authoring_template.md` |
| `## Overview` | 242-244 | 3 | Remove from root (template leakage) | `docs/prompt_templates/readme_authoring_template.md` |
| `## [Core Section: Architecture/API/Usage/Workflow]` | 245-247 | 3 | Remove from root (template leakage) | `docs/prompt_templates/readme_authoring_template.md` |
| `## Quick Start / Examples` | 248-250 | 3 | Remove from root (template leakage) | `docs/prompt_templates/readme_authoring_template.md` |
| `## Developer Notes` | 251-253 | 3 | Remove from root (template leakage) | `docs/prompt_templates/readme_authoring_template.md` |
| `## Further Reading` (template block) | 254-273 | 20 | Remove from root (template leakage) | `docs/prompt_templates/readme_authoring_template.md` |
| `## Development Environment Assumptions` | 274-296 | 23 | Keep in root (condensed essentials only) | Root `AGENTS.md`; `docker/AGENTS.md`, `wctl/AGENTS.md` |
| `## Development Workflow` | 297-399 | 103 | Move detailed workflow out; keep a minimal command entry block | `wctl/AGENTS.md`, `docker/AGENTS.md`, `readme.md` |
| `## Working with NoDb Controllers` | 400-444 | 45 | Move out of root; link only | `wepppy/nodb/AGENTS.md` |
| `## Testing and Validation` | 445-583 | 139 | Move out of root; keep minimal test gate pointers | `tests/AGENTS.md` |
| `## Front-End Development` | 584-679 | 96 | Move out of root; link only | `wepppy/weppcloud/AGENTS.md`, `wepppy/weppcloud/controllers_js/AGENTS.md`, `docs/ui-docs/README.md` |
| `## Common Tasks` | 680-764 | 85 | Move out of root; replace with routing map | Subsystem AGENTS files; `docs/work-packages/README.md` |
| `## Security Considerations` | 765-790 | 26 | Keep short root guardrails + link | `docs/dev-notes/endpoint_security_notes.md` |
| `## Code Style and Conventions` | 791-822 | 32 | Move out of root; link only | `docs/dev-notes/style-guide.md` |
| `## Performance Optimization` | 823-842 | 20 | Move out of root; link only | `ARCHITECTURE.md`, component docs |
| `## WEPPcloud Endpoints` | 843-846 | 4 | Move out of root; link only | `wepppy/weppcloud/AGENTS.md` |
| `## Integration with External Tools` | 847-867 | 21 | Move out of root; link only | `ARCHITECTURE.md`, module/service READMEs |
| `## Further Reading` (resource index) | 868-892 | 25 | Keep but collapse into single "Documentation Map" | Root `AGENTS.md` |
| `## Getting Help` | 893-1040 | 148 | Keep concise escalation guidance; move tooling manuals out | Root `AGENTS.md`; `tools/README.markdown-tools.md` |
| `## Agent-Specific Guidance` | 1041-1084 | 44 | Merge critical deltas into root directives; move remainder | Root `AGENTS.md`, domain AGENTS files |
| `## Notes for Next Pass` | 1085-1094 | 10 | Move out of onboarding doc | `PROJECT_TRACKER.md` (or dedicated dev-note log) |
| `## Credits` | 1095-1100 | 6 | Remove from onboarding; keep in human-facing docs | `readme.md`, `license.txt` |

#### CONTRIBUTING_AGENTS.md Phase 0 Check
| Section (`CONTRIBUTING_AGENTS.md`) | Line Range | Size (Lines) | Phase 0 Decision |
| --- | --- | --- | --- |
| `## Purpose` | 5-9 | 5 | Keep (minor wording updates only) |
| `## Core References` | 10-19 | 10 | Keep and align links with new root map |
| `## Workflow Snapshot` | 20-25 | 6 | Keep; adjust first step to avoid forcing full root deep read |
| `## Change Routing Cheatsheet` | 26-35 | 10 | Keep |
| `## Validation Checklist` | 36-43 | 8 | Keep; align with root validation entry points |
| `## When Something Feels Off` | 44-51 | 8 | Keep |

#### Orphaned Guidance / Destination Gaps Identified
1. `AGENTS.md` "Notes for Next Pass" content does not have a clear long-term canonical owner. Proposed destination: `PROJECT_TRACKER.md` for backlog items, with optional follow-up to create a dedicated dev-note log if needed.
2. WEPPcloud endpoint guidance is currently fragmented across route docs and AGENTS files. Proposed destination: keep canonical endpoint behavior in `wepppy/weppcloud/AGENTS.md`, optionally add a dedicated endpoint index later if discoverability remains weak.
3. External tool integration notes are split across architecture text and subsystem docs. Proposed destination: centralize high-level linkage in `ARCHITECTURE.md` and keep implementation details local to subsystem AGENTS/README files.

#### Phase 0 Outcome
1. Baseline metrics recorded.
2. Section-by-section keep/move/link matrix completed for both onboarding docs.
3. Gap list prepared for Phase 3 cross-link and destination hardening.
4. Phase 1 can proceed without additional discovery.

### Phase 1: Rewrite Root `AGENTS.md` As Map
1. Keep only high-signal global directives and minimum runtime assumptions.
2. Introduce a strict "Documentation Map" section with stable pointers by domain:
   - Architecture
   - Planning/ExecPlans
   - Testing
   - Front-end
   - NoDb
   - RQ/microservices
   - Docs tooling
3. Add a short "Nearest AGENTS Wins" reminder so agents discover local instructions first.
4. Remove long-form tutorials and recipe blocks from root.

Deliverable:
- Refactored root `AGENTS.md` within target size budget.

### Phase 1 Execution Notes (Completed 2026-02-19)

#### Root AGENTS Rewrite Outcome
| Metric | Before | After | Delta |
| --- | --- | --- | --- |
| Lines (`AGENTS.md`) | 1100 | 100 | -1000 |
| Bytes (`AGENTS.md`) | 55,761 | 5,909 | -49,852 |
| `##` headings | 30 | 15 | -15 |
| `###` headings | 64 | 0 | -64 |

Phase 1 decisions implemented:
1. Preserved mandatory global directives in root:
   - Authorship block (verbatim)
   - Core directives (`??`, clarification, terse docs, no silent fallbacks)
   - ExecPlan contract + `docs/prompt_templates/codex_exec_plans.md`
   - Change scope discipline
   - RQ response contract and dependency catalog update trigger
2. Replaced long-form tutorials and recipe sections with map-style pointers to canonical docs and subsystem AGENTS files.
3. Added explicit instruction discovery guidance and "Nearest AGENTS Wins" routing.
4. Added root maintenance guardrails ("Root Exclusions", "Root Size Policy") to reduce regression risk.

Validation evidence:
1. `wctl doc-lint --path AGENTS.md` passed after rewrite.
2. `diff -u AGENTS.md <(uk2us AGENTS.md)` produced no changes.

### Phase 2: Rewrite `CONTRIBUTING_AGENTS.md` As Quickstart
1. Add a concise first-session checklist (read order + initial commands).
2. Keep change-routing table, but trim policy duplication.
3. Add explicit handoff/hygiene expectations for contributors (tests, docs, unresolved blockers).
4. Update "Last Updated" metadata.

Deliverable:
- Refactored `CONTRIBUTING_AGENTS.md` aligned with root map.

### Phase 2 Execution Notes (Completed 2026-02-19)

#### CONTRIBUTING_AGENTS Rewrite Outcome
| Metric | Before | After | Delta |
| --- | --- | --- | --- |
| Lines (`CONTRIBUTING_AGENTS.md`) | 51 | 64 | +13 |
| Bytes (`CONTRIBUTING_AGENTS.md`) | 3,731 | 3,330 | -401 |
| `##` headings | 6 | 8 | +2 |

Phase 2 decisions implemented:
1. Reframed the file as a contributor quickstart with explicit first-session checklist.
2. Aligned references with the new root map and added subsystem entry points.
3. Kept a concise routing table and validation checklist using `wctl` entry points.
4. Added explicit handoff hygiene requirements (scope, validations, assumptions, blockers).

Validation evidence:
1. `wctl doc-lint --path CONTRIBUTING_AGENTS.md` passed.
2. `diff -u CONTRIBUTING_AGENTS.md <(uk2us CONTRIBUTING_AGENTS.md)` produced no changes.

### Phase 3: Cross-Link and Gap Closure
1. Ensure every removed root section has a reachable destination link.
2. If a destination doc is missing, add a small targeted doc stub in `docs/` or relevant subsystem directory.
3. Confirm nested AGENTS references remain valid after root shrink.

Deliverable:
- No dead links introduced by relocation.

### Phase 3 Execution Notes (Completed 2026-02-19)
1. Verified all canonical map destinations referenced from root/contributing onboarding docs exist in-repo (architecture, trackers, templates, subsystem AGENTS files, RQ contract/docs).
2. Confirmed relocated root content families now resolve through the map-style destinations listed in `AGENTS.md`.
3. Retained existing Phase 0 gap notes as follow-up candidates (endpoint index and long-term owner for backlog-style "next pass" notes), but no blocking missing destination remained for onboarding refactor completion.

Validation evidence:
1. Manual path existence sweep across canonical links passed (no missing files/directories).

### Phase 4: Validation and Guardrails
1. Run markdown lint and link/reference checks for touched files.
2. Run spelling normalization preview and apply safe substitutions only.
3. Add a lightweight regression guard (documented policy target) to keep root onboarding compact.

Deliverable:
- Validation evidence in PR notes (commands + results summary).

### Phase 4 Execution Notes (Completed 2026-02-19)
1. `wctl doc-lint --path AGENTS.md` passed.
2. `wctl doc-lint --path CONTRIBUTING_AGENTS.md` passed.
3. `wctl doc-lint --path docs/mini-work-packages/20260219_agents_onboarding_refactor.md` passed.
4. `diff -u AGENTS.md <(uk2us AGENTS.md)` and `diff -u CONTRIBUTING_AGENTS.md <(uk2us CONTRIBUTING_AGENTS.md)` produced no changes.
5. `wctl doc-refs` could not be used due local workspace permission errors under `.docker-data/postgres`; compensated with manual canonical-link existence checks during Phase 3.

### Peer Review Follow-Up Notes (Completed 2026-02-19)
1. Fixed stale work-package onboarding cross-reference in `docs/work-packages/README.md`.
2. Added first-hop NoDb bugfix routing and canonical test-start commands in `wepppy/nodb/AGENTS.md`.
3. Added explicit WEPPcloud -> controllers JS routing note in `wepppy/weppcloud/AGENTS.md`.
4. Reduced validation checklist duplication by making root `AGENTS.md` the canonical command list and keeping contributor-role deltas in `CONTRIBUTING_AGENTS.md`.
5. Added an automated root onboarding size check (`tools/check_agents_size.sh`) and wired it into docs CI.
6. Current onboarding sizes after follow-up edits: `AGENTS.md` 101 lines, `CONTRIBUTING_AGENTS.md` 66 lines.

### Second Peer Review Follow-Up Notes (Completed 2026-02-19)
1. Updated docs CI lint targets from `README.md` to `readme.md` in both source and generated docs-quality workflows.
2. Expanded docs-quality trigger paths to include source workflow inputs:
   - `.github/forest_workflows/docs-quality.yml`
   - `.github/forest_workflows/bootstrap.yml`
3. Added a WEPPcloud "Task Start: Route or Blueprint Changes" block for mixed route/controller onboarding parity.
4. Removed remaining command-list duplication from `CONTRIBUTING_AGENTS.md` validation guidance by deferring exact command forms to root `AGENTS.md`.

## Validation Checklist
1. `wctl doc-lint --path AGENTS.md`
2. `wctl doc-lint --path CONTRIBUTING_AGENTS.md`
3. `wctl doc-refs AGENTS.md`
4. `wctl doc-refs CONTRIBUTING_AGENTS.md`
5. `diff -u AGENTS.md <(uk2us AGENTS.md)` and apply only safe prose changes.
6. `diff -u CONTRIBUTING_AGENTS.md <(uk2us CONTRIBUTING_AGENTS.md)` and apply only safe prose changes.
7. Manual scan: confirm required root directives from "Content Retention Contract" are present.

## Acceptance Criteria
1. Root `AGENTS.md` reduced to target budget (100-160 lines) while retaining required directives.
2. `CONTRIBUTING_AGENTS.md` remains quickstart-oriented (60-120 lines) with no duplicated long-form policy sections.
3. All major domains in current root onboarding have explicit pointer links to canonical docs.
4. No broken links or markdown lint errors in touched onboarding docs.
5. Nested AGENTS model is reinforced (clear nearest-file guidance in root onboarding).

## Risks and Mitigations
1. Risk: Over-trimming removes a critical global directive.
   - Mitigation: Apply the explicit root retention contract and manual checklist before handoff.
2. Risk: Relocated guidance becomes harder to discover.
   - Mitigation: Add stable "Documentation Map" anchors and run `wctl doc-refs` checks.
3. Risk: Policy duplication reappears over time.
   - Mitigation: Add concise size budget notes directly in the onboarding docs and review during doc updates.

## Follow-ups
1. Optional: Add a short "agent onboarding index" doc under `docs/` if future growth requires a dedicated hub.
