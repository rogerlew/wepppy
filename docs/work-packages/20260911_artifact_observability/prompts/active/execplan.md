# Observable Staley artifacts

This living ExecPlan follows docs/prompt_templates/codex_exec_plans.md.

## Purpose and outcome

Users must inspect and archive sources, intermediate maps, diagnostics, failed
attempts and results using the normal project browser. Install the repository
rule and execute a faithful storage migration for addicted-reservist. Numerical
model behavior and payloads are preserved; no rerun is required.

## Progress

- [x] Inspected storage, cleanup, browser filters and actual archive traversal.
- [x] Prepared canonical observability rule, review gates and domain amendment.
- [ ] Independent reviews and checkpoint commit.
- [ ] Implement visible attempt/work writers and explicit audited migration.
- [ ] Add writer/failure/migration and canonical archive/restore tests.
- [ ] Run focused tests; close correctness/security findings.
- [ ] Migrate live project under normal identity, verify browser and archive inventory.
- [ ] Update docs, tracker and validation; archive this plan.

## Context and decisions

Root files are already published by publication.py. production.directory currently
uses .staging, whose paths are embedded in normalized/predictor/result JSON and
NoDb signatures. production.py and dnbr.py are engine-fingerprinted. Migration
must preserve original metadata, rebase JSON dependency hashes, and upgrade only
the exact known storage-only engine version, with an audit. User explicitly
requires observability; hidden sources or cleanup that removes failed work are
unacceptable. Canonical archive walks dot paths today, but browse excludes them.

## Steps

1. Ratify artifacts/contract_decision.md with two independent read-only reviewers
   and commit only its canonical amendments/checkpoint before implementation.
2. Use attempts/<id>, visible normalization output and publication_work/<id>.
   Keep useful failed files/status. Reuse shared locks/path checks and browser.
3. Implement explicit migration: preflight idle state and single-tree layout;
   inventory/back up original JSON/NoDb; rename tree; rebase paths and JSON hashes
   in dependency order; update affected signatures/known fingerprints; save audit;
   publish latest files. No payload recomputation or silent tamper acceptance.
4. Test absent, working, failed, completed, legacy, tampered and interrupted states
   with real files. Exercise canonical archive/restore and compare bytes. Run
   targeted pytest via wctl; full suite is on hold. Review source independently.
5. Execute live migration in rq-worker for /wc1/runs/ad/addicted-reservist; compare
   raster/parquet hashes and model values, NoDb freshness and downloadable files.
   Inspect normal browser and archived inventory. Keep evidence under artifacts/.

## Surprises & discoveries

- Existing archive traversal does not blanket-exclude dot directories. The
  confirmed defect is browser invisibility and reliance on nonportable dot storage.
- Legacy metadata binds path names and checksums; a bare rename breaks reuse.

## Validation and recovery

Tests must execute real filesystem writes and archive generation/restoration.
Migration rejects active operations or conflicting attempts trees, validates
accepted signatures before trusting them, and retains a visible inventory and
exact original metadata. On failure, record status and recover explicitly using
those backups; do not bless changed payloads or discard evidence. Re-running a
completed migration is a no-op. New scientific defaults are out of scope.

## Outcomes & retrospective

Pending implementation and live evidence. Completion requires all gates above.
