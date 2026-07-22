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

## Implementation Re-review (2026-07-22 UTC)

**Reviewed implementation**: WEPPpy working tree following contract checkpoint
`bf5f2e62c`; wepppyo3 commits `3aedb43` and `6b05234`.

- Planck (code): **GO to M3 / HOLD M4**. Verified raw-MUKEY/hillslope
  intersection anchoring, primary-plus-added eligibility, primary-only global
  donor, vector scoring, and selected-only donor publication.
- Mendel (security/operations): **GO to M3 / HOLD M4**. Verified the native
  release import/provenance, artifact checksums/metadata/path rules, and donor
  cleanup/retry. Unreachable immutable files after a failed pre-manifest
  publication are an operations retention follow-up, not a correctness block.
- Newton (QA): reported two narrow M1/M2 blockers: exact primary-raster parent
  validation and per-record support-read global fallback. Both are now
  implemented and focused-tested; Newton confirmed **GO to M3 / HOLD M4**.

Focused evidence: 32 WEPPpy tests, native crate 7/7 with the host PyO3 link
argument, deployable py312 release import, test-stub check, changed-file
broad-exception check, and RQ route-contract check all pass. This lifts the
implementation hold through M3 only. It does not resolve the M3/M4 findings in
the table, so the release/RQ hold remains in force.

## M5 Final Disposition (2026-07-22 UTC)

**Disposition owner**: Codex implementation owner

**M5 reviewed base**: `8dac222dfdd7d54eead918526dc9c6bb488191d0`

**Supplemental implementation/evidence commit**:
`a334ced452ce707123acf920f0ac3d62352a219e`
**Independent reviewers**: `m5_code_review`, `m5_qa_review`, and
`m5_security_review` (all read-only). Their reviewer, turn, base, evidence,
and results are recorded in the companion review artifacts.

The following entries supersede the initial scaffold statuses above. No finding
is accepted as a risk or deferred. `resolved` means the reviewer observed the
implementation and its cited executable evidence; all required implementation
commits are descendants of contract checkpoint `bf5f2e62c`.

| Review | ID | Severity | Owner | Status | Reviewer-visible verification and implementation evidence |
| --- | --- | --- | --- | --- | --- |
| Code | CR-01 | High | Codex | resolved | Primary-only global selection and origin-neutral candidates: `1dcce3bba`; focused suite / adversarial corpus. |
| Code | CR-02 | High | Codex | resolved | Primary and added candidate eligibility plus selected-only materialization: `1dcce3bba`; M2/M3 fixtures. |
| Code | CR-03 | High | Codex | resolved | Validated persisted raster, checksum/provenance, and materialization-failure recovery: `91ad300e4`, `2d0eebdfe`. |
| Code | CR-04 | Medium | Codex | resolved | Residual-invalid dominant-only trigger and no-op matrix: `1dcce3bba`, `2d0eebdfe`; M4 all-valid RQ evidence. |
| Code | CR-05 | Medium | Codex | resolved | Profile/range/texture/scale/radius/support/numeric-tie matrix: `1dcce3bba`, `791198bc2`. |
| Code | CR-06 | Medium | Codex | resolved | Additive nullable provenance, Parquet, hydration, and generated-output proof: `33087ccfa`, `2d0eebdfe`. |
| Code | CR-07 | Medium | Codex | resolved | Explicit native dependency failure, nonbuildable exclusion, and atomic retry: `1dcce3bba`, `a334ced45`. |
| Code | CR-08 | Medium | Codex | resolved | Per-occurrence WGS84 locations and disconnected-location selection fixtures: `1dcce3bba`, `2d0eebdfe`. |
| QA | QA-01 | High | Codex | resolved | Origin-neutral primary/added eligibility: `1dcce3bba`; QA 42/42 evidence. |
| QA | QA-02 | High | Codex | resolved | Materialization failure, clean retry, and global provenance: `2d0eebdfe`; QA 42/42 evidence. |
| QA | QA-03 | High | Codex | resolved | All-valid RQ `not_attempted`, no artifact, unchanged assignments: M4 acceptance record, `6a0e053e7`. |
| QA | QA-04 | Medium | Codex | resolved | Collection-unavailable versus nonbuildable versus missing-native matrix: `1dcce3bba`, `2d0eebdfe`. |
| QA | QA-05 | Medium | Codex | resolved | Cross-artifact helper and hermetic/RQ propagation evidence: `33087ccfa`, `2d0eebdfe`. |
| QA | QA-06 | Medium | Codex | resolved | This append-only ledger plus three M5 review records provide reviewer, base, evidence, result, and zero-unresolved closure. |
| QA | QA-07 | Medium | Codex | resolved | Traceable scoring fixture matrix and adversarial corpus: `791198bc2`, `2d0eebdfe`. |
| Security | SEC-01 | High | Codex | resolved | Root-contained manifest-last publication, stale/symlink checks, and independently run concurrent failure/retry test: `a334ced45` (1 passed). |
| Security | SEC-02 | High | Codex | resolved | Canonical configured-root resolver and source-containment tests: `1dcce3bba`; security review. |
| Security | OPS-01 | High | Codex | resolved | Correct RQ operation, poll, redacted acceptance transcript: `6a0e053e7`; M4 RQ acceptance artifact. |
| Security | SEC-03 | Medium | Codex | resolved | Normalized config-match precondition with no-mutation error test: `1dcce3bba`; RQ route suite. |
| Security | OPS-02 | Medium | Codex | resolved | Targeted local RQ preflight/recovery and health evidence: M4 RQ acceptance artifact. |
| Security | GOV-01 | Medium | Codex | resolved | This append-only disposition names all findings and M5 independent reviewer metadata, evidence, results, and gate calculation. |

## M5 Final Gate

- **Code review**: GO; zero unresolved critical/high/medium findings.
- **QA review**: GO; zero unresolved critical/high/medium findings.
- **Security review**: GO; zero unresolved critical/high/medium findings.
- **Disposition complete**: yes; 21 of 21 findings resolved, zero accepted
  risks or deferrals.
- **Package close recommendation**: GO, subject to the recorded final release
  gates.
