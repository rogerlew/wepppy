# MIPA-01 producer implementation security review

## Findings first

| ID | Severity | Surface | Finding and evidence | Required remediation | Status |
| --- | --- | --- | --- | --- | --- |
| SEC-01 | High | New staged management rewrite | The initial `pmetpara.py` implementation wrote every selected management with `Path.write_text`, following child symlinks and modifying shared hardlink inodes. A direct container reproduction succeeded while changing the external source bytes for both link types. | Publish source-preserving staged copies; reject child symlinks/nonregular inputs and outputs under the existing run boundary. Exercise ordinary files, hardlinks, symlinks, failure and retry without replacing the real writer. Include the PMET destination in the shared publication assessment. | Resolved at the local source boundary; see remediation readback below |

## Scope and status

Reviewer: dedicated security agent `mipa_security_review`, 2026-11-02.
Contract ancestor: `4579b11ce`. This review records the initial finding,
remediation and final source-security disposition. Correctness/QA and release
gates remain independent. The approved
[MOFE input identity contract](../../../schemas/mofe-input-identity-contract.md)
and existing upload/persistence/artifact contracts remain authoritative.

Reviewed surfaces are `wepppy/wepp/management/pmetpara.py`, the management parser
and serializer metadata changes, Disturbed preparation, and the owned Rust slope
writer at `/workdir/wepppyo3/wepp_interchange/src/mofe.rs`. No production code or
tests were edited by this reviewer. The documentation workflow uses the
docs-maintainer skill; this review creates only this artifact and disposable
container fixtures.

Security triage is **high**, with a dedicated review required. PMET preparation
previously read management files and wrote one sidecar; it now rewrites management
graphs as well. The new write boundary must preserve source isolation independently
of whether all crop/coefficient assertions pass.

## SEC-01 direct reproduction

Command boundary: `wctl exec weppcloud python -c ...`, using the real
`pmetpara_prep` and the existing `HIGH_SEVERITY_FIRE_MAN` fixture. A disposable
temporary directory contains an external `immutable-source.man`, a `runs/`
directory and `runs/p1.man` linked to that source. Each call uses scalar
coefficients 0.95 and 0.8. No production project, immutable uploaded artifact or
retained native evidence was used or changed.

Executed `pmetpara.py` SHA256:
`5214570da7bffa54557bd2fc5b9e0327b89f76688b65e14cbad259f283df0e3b`.

| Link type | Source bytes changed | Staged path remains symlink | Source/stage inode remains equal |
| --- | --- | --- | --- |
| Symbolic link | true | true | true |
| Hardlink | true | false | true |

This is direct filesystem evidence of the new mutation, not a claim that an
unauthenticated endpoint was exploited. Normal run access remains authorized;
the important boundary is that selecting a generated file must not authorize
overwriting another artifact through a link. The repository's existing
`copy_input_file` helper can create hardlinks, although this review has not proven
a current management-preparation call site uses that helper for `.man` files.

The smallest repair must retain valid ordinary and hardlinked staged-file use
without changing external bytes. Child symlinks/nonregular files may fail through
the contract's existing malformed-state policy. A check before a later truncating
open alone is insufficient to protect against link replacement; final publication
must not follow the destination link. Do not introduce a new service, queue,
artifact store or hidden retained output for this fix.

## Surface assessment

No route, session, JWT, CSRF, secrets, external dependency, network-egress or
queue-topology delta was found in this bounded source diff. Auth and NoDb
ownership remain with existing callers; this review does not reapprove those
unchanged systems. The newly parsed provenance is JSON data, not executable
deserialization. Generated aliases are restricted to native-token-safe names and
coefficients are checked for finite numeric values.

The current writer renders/validates all management graphs before starting its
write loop. Mapping or graph validation failures therefore occur before
publication. Disk-write failures still require real tests demonstrating an
explicit failed preparation, visible useful artifacts and normal regeneration
on retry. A partial set of new managements plus an old PMET table cannot be
reported as ready merely because files exist.

Rust slope validation rejects invalid enabled buffers and unrepresentable lengths
before `File::create`. The output path and publication mechanism are unchanged
by that slice. This review does not claim Rust source/binary equivalence, native
model acceptance, or that every historical slope path is secured.

## Valid-state and artifact gates

Required noninterference states include ordinary single-OFE inputs, empty PMET
collection, valid legacy names, populated MOFE state, immutable uploads, legitimate
hardlinked staged files, malformed child links, missing/contradictory provenance,
failed preparation, retry and archive/restore. The implementation test suite is
still evolving; this interim artifact does not mark these all verified.

The contract retains ordinary `landuse/`, `soils/` and `wepp/runs/` files and job
diagnostics under normal browse/download/archive authorization. No new hidden
output or archive exclusion is authorized. The final readback below closes local
archive/restore and failure-retention evidence and assesses the retained actual
project preparation. Normal browse/download and complete worker-orchestration
evidence remain separate gates; missing observations are not approved exceptions.

## Native boundary and verdict

NATIVE-01/02/03 remain separate known dependencies. In particular, the existing
rotation-synthesis limit of 20 plants does not establish the executable's PMET capacity;
the audited native reference has six coefficient slots. Graph splitting may add
crop scenarios, so producer correctness cannot authorize execution across that
capacity or resolve the FC/HK ownership HOLD. No silent producer cap or native
repair is authorized by this review.

Initial gate: **fail / hold**. Initial findings: high 1, medium 0, low 0.
SEC-01 was subsequently remediated and independently replayed as recorded below.
Release sign-off still requires independent correctness/QA and disposition of the
required environment/artifact/native evidence.
No risk acceptance is recorded. Deployment and existing-project regeneration are
outside scope and remain unapproved.

## SEC-01 remediation readback

The primary agent replaced truncating management writes with exclusively created,
visible attempt files and `os.replace` of generated directory entries. Existing
regular-file modes are applied before writing content; new files retain umask
semantics. Child symlinks/nonregular destinations are rejected by `lstat` checks,
and the sidecar is prevalidated before any management publication. Replacement
does not modify a shared hardlink inode or follow a destination symlink. Failed
attempt files remain visible for existing failure status and normal retry.

The parser's validated provenance is now the single authoritative read snapshot;
the former separate metadata read has been removed. No additional metadata race
finding is retained.

Reviewed/replayed `pmetpara.py` SHA256:
`b43fd3dc6e5b74d2666428f1adfc2a9d1ab0ae8f0fed423c2a2a3ecc76bbf50a`.
Related `managements.py` SHA256:
`1ed70b4bd4380673141b4600e60d021e3fc66e87aac916daa5cc156d3a1466d8`.

Independent replay used the same disposable container fixture approach:

| Case | Result | Source byte preservation | Generated inode/mode |
| --- | --- | --- | --- |
| Symlink management | Explicit `ValueError` | Unchanged | Link not followed for publication |
| Hardlinked management | Preparation succeeds | Unchanged | Separate inode, retained mode `0640` |
| Hardlinked existing PMET sidecar | Preparation succeeds | Unchanged | Separate generated inode |

Focused canonical test command:

    wctl run-pytest tests/wepp/management/test_mofe_input_identity.py -k 'linked_source or sidecar_symlink or provenance'

Result: **4 passed, 10 deselected**. Tests exercise real writers and parsers,
prove management symlink rejection, hardlink source preservation and retained
mode, reject a sidecar symlink before management writes, and retain original-name
provenance across ordinary read/write while rejecting lost metadata.

SEC-01 is closed for this source snapshot. No unresolved high/medium/low security
source finding remains. The subsequent canonical command
`wctl run-pytest tests/wepp/management/test_mofe_input_identity.py -k failed_replace`
passes **1 test, 16 deselected**. It injects publication failure at `os.replace`
after actual rendering and file writes, proves the previous destination remains
unchanged and the visible attempt parses correctly, then removes the injected
fault and proves retry publishes the same bytes. This is local failure/retry
evidence, not a claim of observed operating-system disk exhaustion or worker status.

The canonical contract now inventories the new visible pattern
`wepp/runs/<filename>.mipa-<uuid>.tmp` and its retry/status behavior. At this
intermediate readback, archive/restore byte evidence remained pending. Static inspection
of `project_rq_archive._is_archive_excluded_relpath` finds no suffix-based exclusion
for these files; that observation is not a substitute for an executed archive test.

Intermediate recommendation: **local security-source review passes; release/package
acceptance remains HOLD** for final correctness/QA and the separately recorded
artifact/environment/native gates. This is not risk acceptance or deployment
authorization. Later changes to the reviewed publication helper require renewed
source/readback review.

## Final snapshot and artifact readback

The final readback retains SEC-01 closure. Final reviewed source hashes:

| Source | SHA256 |
| --- | --- |
| `pmetpara.py` | `6e5ed8973c92c356a2527eb06ba2f9bd697df97b3c77abe60ff3cc07ae1fad3f` |
| `managements.py` | `c83275c7b2dd5331f991086158b3a2605a056c9431551d388128391872842664` |
| `utils/multi_ofe.py` | `834787b7d53d778686f3aae834133072a3dfeab48ca225351c175a3c9e1dc8e4` |

The source-preserving publication helper is unchanged from the corrected replay.
The final parser validates partial provenance against existing plant names and
attaches it to each plant scenario. Serialization reconstructs the header from
those scenarios, preserving metadata across mixed prepared/unprepared synthesis.
Aliases include original name, coefficients and physical plant definition. These
changes introduce no new path, deserialization or execution boundary; provenance
remains validated input data rather than proof of a trusted author.

Independent final canonical command:

    wctl run-pytest tests/wepp/management/test_mofe_input_identity.py tests/rq/test_project_rq_archive.py -k 'linked_source or sidecar_symlink or provenance or failed_replace or pmet_identity_and_failed_attempt'

Result: **9 passed, 74 deselected, 3 deprecation warnings**. This binds current
source to link/source-preservation, provenance/synthesis, failure/retry and real
archive/restore coverage. The archive regression executes the canonical archive
and restore implementations, checks ZIP member bytes for management, PMET and a
visible attempt file, restores over a later partial management and repeats PMET
preparation. The archive attempt payload is synthetic; the separate failed-replace
test produces and parses an actual failed attempt. Together these close local
archive-byte retention and retry evidence without claiming an observed disk fault
or live worker failure status.

Retained [supported-fork evidence](actual_project_fork_v2.json) and
[preparation readback](actual_project_prepared_v1.json) record 72 hillslopes and
235 OFEs under UID 1000/GID 993, an unchanged source manifest and byte-identical
repeated PMET preparation. The coefficient receipt checks serialized year/crop
references against final assignments and soils for all 235 elements. It contains
24 table rows but only one distinct coefficient pair, so distinct-coefficient
selection depends on the discriminating fixture coverage. This reviewer inspected
the receipts and producing scripts; the parent performed the actual-project run.
The [coefficient receipt](actual_project_coefficients_v1.json) binds the preceding
`pmetpara.py` hash `3147811ab922641633c0366da8d6c65a6a1e02f95d6468258023a5ee6f0fe7b3`;
the parser and synthesis hashes are unchanged. The final PMET edit removes newly
introduced count guards, while the publication helper is unchanged. The focused
security set passed on both snapshots. The actual-project receipt is not claimed
to execute the final source snapshot.

Final source-security disposition: **pass**, with unresolved findings High 0,
Medium 0, Low 0. Correctness/QA must independently close their findings. The local
archive gate is closed; live browse/download and complete production-equivalent
orchestration evidence are not established by these tests. NATIVE-01/02/03 and
native/release acceptance remain **HOLD**. The installed Rust receipt identifies
its Python wrapper, which alone does not bind the native extension. No native
model run, capacity approval, risk acceptance, deployment authorization or
existing-project regeneration approval is inferred. Publication-helper changes
require renewed review.
