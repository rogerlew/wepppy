# Review Disposition - SSURGO Intelligent Fallback M4 Rollout

## Purpose and Closure Rule

Append-only ledger for independent code, QA, and security reviews. Every
finding must appear here before package closure. `accepted-pending` is
unresolved: it cannot satisfy the M1 gate for high findings or package closure
for any high/medium finding. An accepted risk or deferral requires user approval
in addition to an owner and rationale.

**Reviewed base**: `def1d3243` plus uncommitted M4 scaffold
**Disposition owner**: Codex implementation owner
**Disposition date**: 2026-07-22 UTC

## Finding Disposition

| Review | ID | Severity | Owner | Status | Disposition and required verification | Implementation evidence |
| --- | --- | --- | --- | --- | --- | --- |
| Code | CR-01 | High | Codex | accepted-pending | Keep global mode primary-only; fixture proves added candidates cannot change it. Required before M2. | pending |
| Code | CR-02 | High | Codex | accepted-pending | Implement origin-neutral valid-candidate eligibility and selected-added-only materialization. Required before M2. | pending |
| Code | CR-03 | High | Codex | accepted-pending | Use only validated persisted map; inject materialization failure and prove atomic global fallback. Required before M3. | pending |
| Code | CR-04 | Medium | Codex | accepted-pending | Add dominant-hillslope-only trigger and non-dominant no-op test. Required before M3. | pending |
| Code | CR-05 | Medium | Codex | accepted-pending | Add exact profile/range/texture/scale/radius/tie matrix. Required before M3. | pending |
| Code | CR-06 | Medium | Codex | accepted-pending | Implement and verify the recorded additive schema contract. Required before M3. | pending |
| Code | CR-07 | Medium | Codex | accepted-pending | Add explicit native-dependency error, per-candidate exclusion, and atomic retry tests. Required before M3. | pending |
| Code | CR-08 | Medium | Codex | accepted-pending | Persist per-occurrence locations and test disconnected same-MUKEY selection. Required before M3. | pending |
| QA | QA-01 | High | Codex | accepted-pending | Duplicate independent confirmation of CR-02; prove primary/added eligibility. Required before M2. | pending |
| QA | QA-02 | High | Codex | accepted-pending | Duplicate independent confirmation of CR-03; verify clean retry and `donor_materialization_failed`. Required before M3. | pending |
| QA | QA-03 | High | Codex | accepted-pending | Persist/check `candidate_preparation=not_attempted` and spy zero candidate work in all-valid proof. Required before M4. | pending |
| QA | QA-04 | Medium | Codex | accepted-pending | Distinguish unavailable collection, nonbuildable donor, and missing native support. Required before M3. | pending |
| QA | QA-05 | Medium | Codex | accepted-pending | Add cross-artifact integrity helper and run it hermetically/RQ. Required before M4. | pending |
| QA | QA-06 | Medium | Codex | accepted-pending | Complete closure metadata and zero-unresolved calculation. Required before M5 closure. | pending |
| QA | QA-07 | Medium | Codex | accepted-pending | Add traceable scoring fixture matrix. Required before M3. | pending |
| Security | SEC-01 | High | Codex | accepted-pending | Implement root-contained atomic candidate artifact lifecycle and adversarial/retry tests. Required before M1 implementation. | pending |
| Security | SEC-02 | High | Codex | accepted-pending | Implement canonical source resolver and trust-boundary tests. Required before M1 implementation. | pending |
| Security | OPS-01 | High | Codex | accepted-pending | Use corrected RQ operation discovery/submission/polling transcript. Required before M4. | pending |
| Security | SEC-03 | Medium | Codex | accepted-pending | Add or explicitly disposition tested config-match precondition before mutable POST acceptance. Required before M4. | pending |
| Security | OPS-02 | Medium | Codex | accepted-pending | Follow documented preflight/recovery and health evidence for any local restart. Required before M4. | pending |
| Security | GOV-01 | Medium | Codex | accepted-pending | Preserve append-only review metadata/ledger and enforce zero unresolved high/medium. Required before M5 closure. | pending |

## Final Gate

- **Code review**: HOLD; 3 high and 5 medium unresolved.
- **QA review**: HOLD; 3 high and 4 medium unresolved.
- **Security review**: HOLD; 3 high and 3 medium unresolved.
- **Disposition complete**: no; all 21 findings are recorded but remain
  accepted-pending.
- **Package close recommendation**: HOLD. The minimum release condition is
  zero unresolved critical/high/medium findings, each with a reviewer-visible
  verification result and implementation commit SHA.
