# Fork destination project page

Status: Accepted after independent review on 2026-11-20. Implementation conformance pending.

## Project entry and recovery

An existing authorized project URL is the entry point during and after a fork.
Once a matching root fork job has finished copying and preparing its inputs,
an active fork with regular required core files may render the project and show “This project is still being prepared.” If the core files are
still missing or the copy is active, show a status page at the same URL with
the same message. A status-only response skips query target resolution and
query cookie issuance, including when the destination directory is absent.
For a failed fork with a confirmed copy boundary and the core files present,
keep the project page accessible.
If verified job evidence shows that the copy succeeded and postprocessing
failed, show “The project was copied, but postprocessing failed.” Identify the
failed step by an allowlisted label. Mention that the WEPP simulation finished
only when a matching simulation job succeeded. A failed fork without these
facts shows a generic failure message. If core files are missing, show the
failure on the status page. Ordinary projects and successful forks retain
normal page entry without a fork status notice.

Read the planned receipt and destination job pointer together. Both must
identify the same job and exact destination. Match the root job's fork
function, fork-archive queue, source and destination arguments. A job used
for result or failure details must be registered on that root and match the
expected target, function and terminal status. Missing legacy job records cannot
prove a specific fork failure. Malformed or mismatched records yield an
unlinked generic status for an independently authorized owner and fail
closed for a destination without verified ownership. Add the validated root
job's existing details link and a source fork-console link only after
independent source authorization. The details link works without fork-console
browser storage. Mark fork status responses private and noncacheable. A valid pending or failed receipt
for an ownerless destination also requires source authorization before
displaying its status or project. Preserve ordinary legacy entry when both
fork records are absent.

Check regular core files without following symlinks or opening special files.
Use fork-console core files plus the climate and watershed controllers
required by the project page. A matched root must confirm the copy boundary
before the web process hydrates any forked controller. A known incomplete
copy or missing required
inputs gets the status-only response. Genuine corrupt metadata and unrelated
page failures continue through existing error handling. Check the full current receipt
identity used for display before returning receipt-derived details or a project response and
discard the response if the destination changed during rendering.

Preserve the query authorization checks, ownership, and RQ lifecycle rules.
For a blocked destination, leave query-backed controls unavailable and explain
why. The project page does not submit, prepare, retry, or rerun the fork or
WEPP. A later page visit reads current state. [Query credential handling](../../schemas/query-engine-http-access-contract.md#browser-transport-and-lifecycle)
governs cookie issuance.

## Run page result readiness

For an admitted project or a successful fork, the WEPP loss-map controls use
the [catalog readiness handshake](../../schemas/query-engine-http-access-contract.md#gl-catalog-readiness-handshake)
on demand when a query-backed layer is selected. Use the configured target
endpoint for that page's exact run and config. Supported legacy targets
outside these controls retain their existing query behavior. Active and
failed fork pages do not send catalog preparation or result requests for
these controls. Share a bounded readiness
check per query target and use query wait mode to recover catalog invalidation
between readiness and execution. While waiting, announce “Preparing watershed
results…” near the result controls. Keep independent controls usable and load
the selected result automatically when ready. On timeout or unavailable
catalog, show an explanation and a Retry button for the selected result.
Retry checks catalog readiness and reloads that result. A superseded result
must not repaint the map or replace the active notice.

The project page is independently authorized and may be useful during recovery.
A query cookie conflict cannot substitute for page authorization or provide
query access. Scoped catalog checks keep independent settings and navigation
available and avoid query-catalog work on page entry.
