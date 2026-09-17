# After-restart archive and profile retention acceptance

**Executed after restart: bounded PASS.** See
[runtime evidence](runtime_archive_security_review.md) and the retained first
execution manifest/log. `runtime_archive_acceptance.py` is a standalone
disposable acceptance driver. Its earlier preparation/syntax validation was not
runtime acceptance. Parent owns restart, live authentication, global canary and
final operation-matrix disposition; live HTTP and optional profile controls stay
separate from the completed native/helper/archive operation.

## Execution boundary

After the affected service restart, run the script through the existing wctl
container-exec entry point as the ordinary non-root service UID/GID, with
`--restart-evidence <retained-restart-evidence-file>`. It records that evidence
file's path/hash, actual identity/groups, a unique new project and result path.
It does not restart services, load credentials, alter auth or reuse an existing
project. It creates only
`/wc1/batch/qa-freshness-archive-<uuid>/runs/archive`; all successful/failed
attempts, archive and manifest remain retained. Each invocation has new artifact
filenames, so a failure is not overwritten by a later successful run.

The driver calls actual Geneva geometry/alignment services on newly generated
tiny GTiffs, checks generated features/class pixels and complete attempt status,
then creates one deliberate failed `_Attempt` with a readable partial candidate
inside private ancestry. The failed attempt must preserve accepted geometry.
No scientific/model result, native reader or publication helper is mocked.

It invokes canonical `archive_rq`/`restore_archive_rq` with actual ZIP/filesystem
and project lifecycle guard. Existing `ArchiveRuntime` supplies only disposable
job/status/path transport and empty project-lock/cache fixtures; this is not a
live RQ submission. Every ordinary file and directory is inventoried. ZIP mode
records, restored bytes/modes and accepted/failed/intermediate retention must
match exactly, including0700 attempts and0600 status files. The restored geometry
must reuse its accepted artifact without creating another attempt.

Normal browse listing and download helpers are exercised before and after the
roundtrip, with actual file responses hashed from their streamed ASGI bodies.
No listing overrides, manifest fabrication or file filtering is supplied. This
proves owner/helper visibility and byte delivery, not live authorization. The
manifest emits the ordinary batch browse URL for parent to visit through the
existing authenticated session after restart. Require actual200 listing and
download responses, reject redirect-to-login/404 as success, and preserve current
private/public/root-only access rules. Do not copy private artifacts elsewhere
to make browsing appear to pass.

## SBS profile provenance boundary

S02 receipts live under the configured recorder **data repository**:
`profiles/_drafts/<run>/<capture>/seed/uploads/sbs/events/<event-hash>`, then under
the promoted profile's `capture/seed/uploads`. `ProfileAssembler.promote_draft`
copies that capture tree and optional run snapshot. These external receipt files
are not automatically members of a normal project ZIP. Moving them into a new
project folder or claiming project archive retention would misstate the actual
owner workflow; no new symlink, allowlist or visibility change is authorized.

Supply repeatable `--profile-seed-root <actual-capture/seed/uploads>` arguments
to read existing disposable S02 capture/promoted trees. The driver verifies each
complete receipt through the actual reader, requires failed records to remain
unusable for replay, and compares their complete bytes/modes before/after the
project roundtrip. It never mutates those roots or fabricates profile receipts.
This is a read-only external-repository control, not profile archival acceptance.

Final S02 evidence must separately retain actual recorder capture, promotion,
two distinguishable event payloads, failed/required receipt behavior and canonical
`wctl run-test-profile` HTTP playback under the existing profile repository's
access model. Use the already retained assembler/promotion/Requests probes and
actual performance evidence for their bounded claims only. If external profile
archival or browser exposure beyond the current owner workflow is required,
first identify its existing canonical operation; do not invent a new archive
protocol or broaden the root-only recorder path policy in this work package.

## Required result and limits

Retain the original failing manifest/log if any assertion or native operation
fails. Successful result requires mode/byte equality, real accepted outputs,
retained failed candidates/status, verified helper downloads and stable optional
profile controls. Record source-module hashes and restarted service/image IDs
with parent runtime evidence; a script result alone is not proof that every
long-lived process loaded this revision. Native full-watershed execution, live
RQ/HTTP transport, archive owner/ACL/mount permutations and broader package
operation-matrix rows remain distinct gates.
