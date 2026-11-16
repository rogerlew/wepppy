# OSR-01 / UFS-01 independent contract security review

## Findings

| ID | Severity | Surface | Finding | Required action | Status |
| --- | --- | --- | --- | --- | --- |
| CS-01 | Medium | Saved-map child association | Exact saved `sbs_file_path` matching does not disambiguate child ownership when two saved SBS definitions have different staging paths but the same basename. The existing scenario-name function maps both to one child. A consumed input can therefore resolve another saved input's bytes through the newly authorized child lookup. | Specify that child lookup requires an unambiguous saved-definition-to-child association. With distinct saved paths targeting one child, reject child recovery with actionable guidance; do not change public naming or require a migration. Retain a direct regression with different raster bytes under equal basenames. | Resolved in contract; implementation regression pending |

Evidence: `wepppy/nodb/mods/omni/omni.py::_scenario_name_from_scenario_definition`
constructs SBS scenario names solely from the base64-encoded basename.
`wepppy/nodb/mods/omni/omni_sbs_freshness.py::child_source` uses that name and
basename. The proposed domain contract's “Saved association and two-location
resolution” section authorizes child lookup from the exact saved definition but
does not distinguish two definitions mapping to the same destination. Its generic
“ambiguous saved associations” rejection should explicitly include this case.
The UI permits multiple SBS rows; this is a reachable data-integrity risk rather
than a cross-project access claim. An attacker with run-edit permission could
intentionally create the ambiguity, and ordinary same-name uploads could do so
accidentally. No runtime exploit was executed in this contract-only review.

## Metadata and verdict

Reviewer: independent `security_reviewer` agent `/root/contract_security`.
Date: 2026-11-16 UTC. Base: `65fa0c0bd008b16157a82191a766a0bdb9453173`.
Reviewed the contract decision, new shared staging and Omni SBS contracts,
freshness/upload contract diffs, current admission/helpers, parser, scenario naming,
and controller selection behavior. No implementation edits were reviewed.

Security impact is **high** because admission gains a saved-file resolution and
copy path. This is a pre-implementation contract gate, not final release approval.
**Gate: pass for the contract checkpoint** after CS-01 disposition. Unresolved:
zero high, zero medium, zero low. Final code/security/valid-state evidence remains required independently.

## Surface assessment

The proposal preserves route/session/run authorization, upload extension and
size limits, restricted raster decoding, NoDb locking, and existing queue wiring.
No new secrets, external egress, process invocation, dependency, privilege, or
service is authorized. Filename display explicitly uses text-safe DOM rendering.

The shared contract correctly distinguishes a client selection claim from
filesystem authority, requires server-owned association and containment, preserves
accepted input on failed replacement, and forbids selecting unreferenced files by
enumeration. Unique replacement staging protects accepted files from row-index
collisions. Unknown references and arbitrary paths fail before accepted mutation.

Fork/restore mapping is constrained to the current run and persisted suffix;
implementation must exercise root and destination containment with nonexistent
staging parents as well as symlinked ancestors. A missing source is a valid state
when the documented child is available. A present invalid/unreadable source must
not trigger fallback. The contract states these requirements without adding new
filesystem locking guarantees.

Historical receipts are not required to discover a valid current input; existing
freshness and execution receipts still govern output reuse. This is consistent
with the user's simple legacy policy and avoids inventing historical integrity
proof. Source restoration must validate/copy before child reset and retain the
association/version checks at state commit.

## Required implementation evidence

Retain scoped real-file tests for known staging input, consumed child recovery,
legacy no-receipt recovery, copied-byte identity, root/ancestor symlinks, traversal,
unknown/cross-run claims, fork remapping, invalid preferred-source nonfallback,
same-basename child ambiguity, and selection/content drift. Verify failed
replacement and later-input failure leave accepted maps usable. Include direct
valid-state and hostile-state coverage at the changed copy/admission boundary.
Security approval cannot substitute for browser or generated-output acceptance.

## Post-amendment disposition

Re-reviewed the updated Omni contract and decision matrix on 2026-11-16 UTC.
The domain contract now explicitly requires rejecting child recovery when distinct
saved references map to one child, including equal basenames, while retaining
exact staged-source selection. This closes CS-01 at the contract level without
changing public scenario names or introducing a legacy migration. The decision
matrix includes that state. The implementation must retain the direct regression.

The updated UI contract also distinguishes validation/precommit failures from
postcommit enqueue errors and transport uncertainty. Normal-reader reconciliation
is required for uncertain outcomes; no false rollback guarantee is made. These
amendments preserve the approved scope. Final implementation and runtime security
acceptance remain outstanding.
