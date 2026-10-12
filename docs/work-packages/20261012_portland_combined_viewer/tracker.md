# Tracker — Portland combined watershed viewer

**Last updated**: 2026-10-12, forest execution

**Phase**: M0–M4 complete; forest ready for rollout. Production remains unchanged.

## Task board

- [x] M0: Refresh all 63 production runs and HTTP evidence; preserve existing ownerless downstream visibility.
- [x] M0: Canonical PCV-01 contract, two independent approvals, accepted ancestor `d75460acc` before runtime edits.
- [x] M1: Current PortlandGroup membership plus explicit server catalog; public/owner/admin grants preserved; mixed/private denial.
- [x] M2: Copy63 runs; native averaged LOSS and catalog preparation with manifest, atomic publication and bounded rollback.
- [x] M3: Deck.gl collection rendering, actual config/complete composite joins, old-link compatibility, generator and safe bounds viewer.
- [x] M4: Browser/identity, full regression and independent evidence reviews complete; existing unrelated frontend lint defect recorded.
- [ ] M5: Separately authorized production deployment/preparation, live parity and seven-day observation.

## Decisions and discoveries

Operator authorized forest implementation, required local commits, stack restarts and dev-agent permissions. Production mutation is excluded. PCV-01 records the admission/compatibility contract; the [decision record](artifacts/2026-10-12_contract_decision.md) retains checkpoint rationale. Existing downstream ownerless access remains unchanged, and no PUBLIC markers are created.

Legacy geometry has repeated polygon fragments for one Topaz hillslope. Preserve every fragment while requiring unique complete WEPP/Topaz mappings. Native averaged LOSS already has positive hectare areas: no model rerun, additional watershed converter or schema/formula change is needed. Missing optional phosphorus preserves required variables.

Independent reviews found and closed unsafe legacy bounds HTML/remote payload handling, forged rollback targets, interrupted publication recovery, incomplete mapping, missing optional phosphorus and missing-map readiness. Controls remain disabled during incomplete loading. Stable Deck.gl data identity avoids repeat geometry processing on color/unit changes.

## Evidence and validation

- [Production inventory](artifacts/evidence/production-inventory.jsonl): deployed revision `84337c967136c6bc50f357fb600c0a44534edf2f`,63 ownerless/non-PUBLIC runs, all LOSS text present, native hill Parquet absent.
- [Forest preparations](artifacts/evidence/forest-preparation.jsonl): all 63 complete; exact source-decimal equality for 24,669 hillslope rows; complete geometry joins and content-addressed writer identity.
- [Source parity](artifacts/evidence/source-parity.json): all 919 original file hashes match fresh read-only production hashes. READONLY preserved.
- [Archive/restore](artifacts/evidence/archive-restore.json): canonical writer and restore on isolated real copied run, every file byte-identical; queue/status adapters isolated.
- Python focused: 32 passed; JS data cases: 9 passed. Full Jest:965 tests / 118 suites passed; changed GL modules pass direct ESLint. Repository frontend lint retains the preexisting `climate.test.js:300` conditional-expect error (no change from the accepted ancestor). Focused stub/isolation checks pass (random-order plugin unavailable). The first broad Python run stopped after 8,764 passes/126 skips on a stale-module fixture import; the corrected full WEPPcloud group passes 1,969 tests and the full repository rerun passed 10,620 tests with 126 skips (5,494 warnings,45:34). The existing regional-template render fixture also now supplies the new server-generated collection URLs.
- [Browser log](artifacts/evidence/browser-member.log), [map screenshot](artifacts/evidence/current-conditions.png): use the final completed receipt for readiness, not intermediate output.
- [Correctness](artifacts/2026-10-12_implementation_correctness_review.md) and [security](artifacts/2026-10-12_implementation_security_review.md): final forest approvals, with no unresolved high/medium findings; production acceptance remains M5.

Final browser audit passed picking, drag-selection preservation, pan/zoom/share, final artifact downloads and all-nine native sample parity. Same stored session returned member200, revoked403, and restored independentAdmin200. Original dev-agent roles are restored and saved browser credentials removed. The owner fixture returned409 readiness after admission; the real PUBLIC fixture returned200. UI gesture rationale is recorded in ADR-0087.

Initial incomplete-run browser attempt showed a visible collection error, not a partial map. An earlier browser run was interrupted to load final review fixes and regenerate writer-provenance evidence; it is not counted as a pass. The first preparation's conservative fragment check failed before publication; verified rollback and retained staging preceded correction. Subsequent review regeneration retains earlier manifests in visible run-local evidence directories.

## Candidate

Implementation candidate: `9c8293008` (core `c1e919210` plus static map-attribution link), descended from the accepted contract checkpoint. Local commit only; no push or production deployment. Final broad regression passed; independent reviews approve forest rollout readiness with the documented baseline lint limitation.

## Handoff

M0–M4 of [the active ExecPlan](prompts/active/portland_combined_viewer_execplan.md) are complete. The handoff retains member/same-session revocation and independent grants, normal artifact browse/download, completed test counts, restored dev-agent roles, exact runtime candidate and reviewer dispositions. Follow the [rollout handoff](artifacts/rollout-handoff.md) for later production work and [operator guide](../../dev-notes/combined-watershed-viewer.md) for preparation/recovery. Keep M5 open until production acceptance and observation are evidenced.

The additional [drilldown receipt](artifacts/evidence/drilldown.json) proves one actual-config run shell under independent Admin after the existing Load Without Migrating link; it does not claim full PortlandGroup-only legacy report/control acceptance. All 919 original source hashes remained unchanged after navigation.
