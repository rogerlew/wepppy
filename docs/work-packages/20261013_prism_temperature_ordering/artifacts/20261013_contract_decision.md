# Contract decision — PRISM temperature ordering

**Execution authorized**: operator requested `execute docs/work-packages/20261013_prism_temperature_ordering` after accepting the midpoint proposal and package. **Starting WEPPpy revision**: `78295c949`. **Starting wepppyo3 revision**: `822b6fe1200d980e9eb434547097c976eafcc38f`. No implementation files changed before this checkpoint. Security impact low; no new privilege, route, file format, or acquisition boundary.

## Canonical set and delta

- New `docs/schemas/prism-spatialization-temperature-contract.md`: exact midpoint rule, input/error boundary, unchanged-writer semantics, existing-channel logs, additive EDDE provenance, and actual consumer acceptance.
- `docs/schemas/edde-v2-experimental-client-contract.md`: supersede only introduced-inversion rejection with ADR-0092 midpoint repair; retain source validation, finite/physical checks, error class, ownership and provenance.
- ADR-0092: accepted midpoint decision; implementation pending.
- ADR-0091: prospective exception to rejection/no-correction language only for ADR-0092; do not waive CLIGEN guards or change other forcing fields.
- `docs/schemas/climate-parquet-lineage-contract.md` , `docs/schemas/prism-historic-climate-contract.md`, and `docs/schemas/nodb-persistence-concurrency-contract.md`: assessed, unchanged. No artifact ownership, preparation/finalization, state mutation, locking, or schema semantics change.

Discrepancy classification: intended numerical behavior change for a confirmed generic spatialization defect. Adjusted finite crossed extrema collapse to their midpoint before existing serialization. Reject source temperature inversions/nonfinite temperatures rather than treating them as a PRISM-introduced defect. The native wrapper retains OSError translation; Python generic paths use ValueError, EDDE DataQualityError. No unrelated parser hardening. The detailed contract distinguishes pre-rounding repair magnitude from output precision and does not promise exact monthly means.

Compatibility: public signatures, return values, existing valid files, NoDb keys, output columns, date/precipitation/auxiliary rules remain stable. EDDE metadata is additive; legacy missing diagnostics mean unavailable. New-output versus occupied-output behavior remains unchanged. No existing project rebuild is part of implementation. Diagnostic counts use existing Python logging/native output, no new artifact directory.

## Regression matrix

| State/input | Outcome/evidence |
| --- | --- |
| New output and finite ordered source | Existing offsets then repair introduced inversions; real writer/WEPP readback |
| Valid/equal adjusted pair | Exact unchanged same-writer values/bytes where applicable |
| Negative temperatures, month boundary, rounding tie | Finite ordered serialization, preserved midpoint before rounding, bounded parity |
| Inverted or nonfinite source temperature; nonfinite temperature normal/result | Explicit established-family input error; no successful result |
| Legacy EDDE manifest without diagnostic key | Reader remains compatible; do not infer zero correction |
| Existing EDDE CLI or companion | Existing rejection and original bytes preserved |
| New/empty/populated scratch project state | Normal build and preparation retain ownership/finalization semantics; no new required state |
| Daily Rust / Python daily / Python breakpoint / EDDE | All four actual writers exercised; breakpoint precipitation records preserved |
| Stale native binary | Identify imported path/hash and fail acceptance; never substitute helper-only proof |

Candidate evidence from `3a455437d` is design evidence only: 24 revisions, 15 repaired days, three successful 20-year WEPP runs. Implementation validation must call patched writers and the rebuilt extension, compare the other 21 cases, add non-EDDE/breakpoint cases, and retain exact consumer evidence. Full suite has a previously observed unrelated SBS failure; rerun and report actual disposition without silently broadening this package.

## Independent reviews and checkpoint

Two independent read-only contract reviews are required by the NoDb contract-first standard; record artifacts and dispositions here before committing the checkpoint ancestor. Implementation remains prohibited until that commit exists. Author: Codex, 2026-10-13 UTC.

Review amendments: add a visible sibling log with working/completed status and canonical archive/restore/browser/download evidence (control C1/C2); distinguish writer-level auxiliary invariance from the existing downstream Historic PRISM dewpoint floor on final Tmin (correctness C1). No new authentication, path serving, archive, or storage abstraction is introduced. Exact numerical rule and public signatures are unchanged.

## Final disposition

Both independent reviews pass: `20261013_contract_correctness_review.md` (M1-COR-01 resolved) and `20261013_contract_control_review.md` (C1/C2 resolved). No unresolved findings remain. The primary author accepts the precise retention and downstream-floor amendments; all promised executable evidence remains pending M2–M4. Commit this checkpoint with the canonical amendments as the implementation ancestor.
