# Correctness review: Omni thinning 30/50

Reviewer: independent Codex `/root/contract_review_b`, 2026-09-20 UTC.
Reviewed implementation against ancestor `e56d610e1` and
`docs/ui-docs/contracts/omni-thinning-contract.md`. Verdict: approve; zero findings.
Full collected-suite coverage completed after snapshot follow-up: 9,169 passed,
99 skipped across initial and continuation runs; see tracker.

## User outcome and valid states

| State | Required behavior | Evidence |
| --- | --- | --- |
| Never used / empty list | New thinning row selects 40%, ground 93% | Jest new-row test |
| Populated / saved selection | 30/40/50/65 hydrate and serialize unchanged | Jest parameterized hydration |
| Legacy run | All old files and IDs/records unchanged | compatibility.txt; legacy MOFE/archive cases |
| Working / failed / completed | Ordinary artifacts retained and restorable | real archive/restore regression |
| Archived/restored | Byte-identical management inputs | real archive/restore regression |
| Invalid request / missing parameter | Existing explicit parser/error behavior | unchanged production parsers; broad suite |

No new user-reachable errors. Existing treatment eligibility, override/RAP
precedence, parameter validation, authentication, worker state and failure
behavior remain unchanged. New selections do not mutate earlier scenario outputs.

## Generated artifact evidence chain

| Stage | Evidence and scope |
| --- | --- |
| Intent / reload | JS hydrated server payloads and serialized percent strings; existing persistence schema unchanged |
| Source | 40 new catalog resolutions across five maps; 8 new files with canopy-only byte changes |
| Single-OFE input | Real WeppPrepService writes p1.man; parser verifies canopy, both grounds and plants for 8 combinations |
| MOFE intermediate | Actual Omni mode/Treatments/landuse synthesis for mixed eligible/ineligible segments |
| Prepared input | Actual MOFE preparation reads/writes p1.man; all 8 covers parsed |
| Archive | Actual archive_rq/restore_archive_rq restores representative new/legacy management bytes |
| Browse/download | Existing service regressions, 38 passed; live browser acceptance unverified |
| WEPP execution/report | Outside local code-delivery scope; no model run or numerical-result claim |

No changed storage, security or persistence boundary. Fixture scaffolding isolates
unrelated raster/soil/external services; the management parser, writer, synthesis,
preparation and archive boundaries are real. No new artifact paths or exclusions.

## Independent checks and disposition

Reviewer independently compared all 8 new files with their sources and parsed all
5 catalogs with duplicate-key detection: exactly 8 additions per map, all legacy
records unchanged. Explicit default and hydration behavior approved. No high,
medium or low findings. Local-input acceptance only; live browser inspection,
production-equivalent execution and deployment remain operator-owned release gates.

## Snapshot follow-up

Independent reviewer rechecked the broad-suite snapshot fix: exactly eight
new classes and count 47, all legacy classes preserved. No findings. Approved
retaining initial and continuation evidence separately; only test expectations
changed after the reviewed implementation.
