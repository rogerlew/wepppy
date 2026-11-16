# Omni SBS reload implementation security review

## Findings

| ID | Severity | Surface | Finding and remediation | Status |
| --- | --- | --- | --- | --- |
| SEC-01 | Medium | Restore publication/data integrity | Initial `_restore_saved_sbs` published a raster into the already-associated staging path before comparing its bytes to the validated child receipt. A child mutation during copying could fail the final check but leave different bytes available at the accepted path. Require staged digest equality and source-identity reassertion before publication. `_validate_copy` now performs both checks in the upload helper's `post_save` callback. | Resolved; retained real-raster regression passes |

Exploit/failure path: an authorized concurrent operation or another writer alters
the selected child after prevalidation but before restore copying. The original
callback checked only raster validity, not equality to the captured input, so
valid changed bytes could be published before rejection. This is a data-integrity
issue inside the run; no cross-run read or privilege escalation was demonstrated.

A real-raster probe against the corrected candidate mutated the child inside the
save call before copying. The actual upload helper rejected it and left no staged
file. Probe output:

    UploadError: Uploaded raster changed after validation.
    {'restored_exists_after_rejection': False, 'restored_equals_original': None}

## Metadata and triage

Reviewer: independent `/root/contract_security` security reviewer.
Review timestamp: 2026-11-16 19:21 UTC. Contract ancestor: `67468cf86`.
Scope: working-tree changes to `wepppy/microservices/rq_engine/omni_routes.py`,
`wepppy/weppcloud/controllers_js/omni.js`, and their scoped tests; unchanged upload,
NoDb, and SBS freshness helpers inspected as dependencies.

Reviewed source SHA256:

- `omni_routes.py`: `c38726154cf89d3e1e296bfc015f55b7c58e1c7e226c3a8a8b478677c297de03`
- `omni.js`: `fa6241c9e3c6b9e1f0e462e79adbb15dc61a076a9163dfdbc1bed9243f50919d`

Security impact: **high**. Dedicated review is required for new saved-file
resolution/copy behavior. No production or external actions performed.

## Boundary assessment

**Authorization and scope:** Existing feature access, run/JWT authorization,
CSRF transport, queue selection and worker graph are unchanged. No new secrets,
network access, subprocess calls, dependency, permissions, or service introduced.

**Association and containment:** Requests select an exact server-owned saved
reference, not current row position or arbitrary path. Staging suffix rebasing
uses only that saved definition and rejects traversal/malformed suffixes. Current
run containment and symlink ancestors are checked before resolving inputs or
writing restored files. Missing ancestors are permitted so a consumed legacy
upload can be restored. Child recovery rejects distinct saved references mapping
to the same child, closing contract finding CS-01. A present invalid source fails
rather than falling through to an older child. Unknown claims cannot select
unreferenced staging files. Existing limits and restricted raster decoding remain.

**Replacement and copy:** Fresh uploads use unique staging directories and retain
old accepted files. All raster candidates are prevalidated before publication.
Child restore uses no-overwrite publication, preventing a concurrent destination
creation from being silently overwritten. Prepublication digest/source checking
now closes SEC-01. Final restored identity is revalidated and checked again at
NoDb commit; selected saved state is compared with a detached read while the
existing lock is held. Existing freshness checks still govern execution and
output reuse. Arbitrary ancestor replacement after containment checks remains
outside the contract's existing filesystem-writer isolation guarantee; no stronger
locking guarantee is claimed.

**Browser and error handling:** Saved filenames are rendered with `textContent`,
including code-formatted basenames. Saved references stay with their file control;
type changes recreate controls without transferring that reference. Compact
multipart indexing matches the submitted scenario list. Reconciliation queries
normal saved state after successful or uncertain requests, preserving error
status instead of claiming postcommit rollback. No new HTML injection sink found.

## Valid-state and evidence limits

The contract state matrix includes never-used/empty, staged, consumed, legacy,
missing, malformed, and hostile states. Added real-raster tests cover staging
selection after row movement, consumed child recovery through actual copy/reset,
legacy recovery without a historical receipt, local fork rebasing, ambiguous
children, invalid/present-source nonfallback, symlinks, traversal, and isolated
replacement. Source review confirms these exercise actual raster helpers rather
than replacing the changed filesystem boundary with mocks.

Reviewed retained regression
`test_saved_sbs_restore_checks_copied_bytes_before_publication`: it changes the
child to a different valid GDAL raster at the copy seam, invokes the real upload
helper, and asserts rejection leaves no restored staged file. The scoped command
below passed **116 tests**, including that regression (7 existing warnings):

    wctl run-pytest tests/microservices/test_rq_engine_omni_routes.py tests/weppcloud/routes/test_omni_bp.py tests/weppcloud/routes/test_omni_bp_routes.py tests/nodb/mods/test_omni_sbs_freshness.py --maxfail=2

Result inspected in `/tmp/omni-scoped-python.log`; the implementation agent also
reported 26 passing Omni JS tests and clean scoped ESLint. Re-reviewed the later
JS saved-definition reader and legacy-type normalization changes; no additional
security finding. Browser/runtime/generated-input acceptance is still in progress
and is not supplied by this security review.
Absence of a code finding is not proof of complete environment acceptance.

## Verdict

**Security implementation gate: pass.** No unresolved high/medium security
findings after the SEC-01 fix and retained passing regression. Unresolved high: 0;
medium: 0; low: 0.
Package release/closure must additionally satisfy independent correctness/UX,
scoped tests, browser and generated-artifact evidence. No deployment approval is
given by this review.

## Final candidate recheck

Re-reviewed the final JS deletion-pruning change: both request construction and
post-delete row pruning now derive the accepted saved definition, so a pending
replacement cannot substitute its name for the accepted map. The retained test
dispatches the file-change event, checks the accepted deletion request, and checks
that the correct row is removed. No new security finding; reviewed JS hash above
is updated. Backend hash is unchanged.

Inspected `/tmp/omni-commit-test.log`: the real NoDb commit success and concurrent
saved-selection drift cases both passed (2 passed). The drift test exercises the
actual persisted controller and commit validator, confirms the new concurrent
selection remains authoritative after rejection, and preserves the staged file.

`runtime_followup.json` records recovery through real admission/NoDb reload,
raster readback, consumption after child reset, 218 generated management/soil/run
inputs and 217 fresh hillslope outputs under UID 1000/GID 993. It also explicitly
records the watershed fixture blocker: channel climate starts in 2007 while
hillslope passes start in 1980. This supports the inspected input lifecycle but
does not establish completed watershed/report acceptance. That package limitation
is not a new security defect and remains visible for closeout. Security gate
remains pass with zero unresolved findings.
