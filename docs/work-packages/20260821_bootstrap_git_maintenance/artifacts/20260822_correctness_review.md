# Correctness Review – Bootstrap Git Maintenance

## Metadata

- **Package**: `docs/work-packages/20260821_bootstrap_git_maintenance/`
- **Reviewer**: Codex
- **Date**: 2026-08-22
- **Scope reviewed**: initial Bootstrap repository creation and maintenance
- **Canonical contract**: `docs/weppcloud-bootstrap-spec.md`

## User Outcome

- **User goal**: clone initialized run repositories without repeatedly paying
  avoidable loose-object packing cost.
- **Success**: initialization finishes, refs/content are unchanged, and later
  clone timing improves or remains correct.
- **Failure**: maintenance failure makes enable fail explicitly; it is never
  silently reported as successful.

## Valid-State Matrix

| State | Required behavior | Evidence |
| --- | --- | --- |
| Repository absent | initialize, commit, hook, maintain, enable | source ordering plus authored regression |
| Repository initialized but enable retrying | repeat safe initialization boundary and maintain | idempotent Git command design; canary validation pending |
| Empty initial managed paths | allow empty commit and maintain | existing `--allow-empty` contract retained |
| Populated managed paths | pack objects without changing refs/content | direct Git test preserved commit and tree SHA and created pack/bitmap |
| Invalid CPU budget at process startup | existing WEPPpy startup validation fails explicitly | existing `NCPU` contract |

## Findings

| ID | Severity | Description | Required action | Status |
| --- | --- | --- | --- | --- |
| COR-01 | High | Maintenance must not mark Bootstrap enabled before successful completion. | Verify call ordering and failure propagation. | Resolved by explicit ordering and authored failure regression |
| COR-02 | Medium | Maintenance must preserve refs and tracked content. | Direct repository test and live before/after evidence. | Resolved for pre-apply by direct repository SHA preservation; live evidence remains a package exit criterion |

## Verdict

- **Gate status**: pass
- **Unresolved findings**: High 0; Medium 0; Low 0
- **Release recommendation**: ship to the private pre-production canary and
  retain live preservation/clone evidence as the package closeout gate
