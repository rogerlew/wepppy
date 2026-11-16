# Omni SBS saved-map control

Status: OSR-01 accepted intent (2026-11-16); candidate implemented and scoped validation passed; no production rollout.

## Scope and authority

Omni adopts the [user-file staging lifecycle](../../schemas/user-file-staging-contract.md)
for SBS maps. This contract covers scenario hydration, multipart submission,
accepted-map presentation, and input resolution. Existing
[upload admission](../../schemas/upload-endpoint-contract.md),
[request payload](../../schemas/request-payload-contract.md),
[RQ responses](../../schemas/rq-response-contract.md),
[controller conventions](../controller-contract.md), and
[NoDb persistence](../../schemas/nodb-persistence-concurrency-contract.md) apply.
[SBS freshness](../../schemas/omni-sbs-freshness-contract.md) owns output reuse
and execution content checks; resolving an input does not bypass those checks.

## UI and transport

`GET api/omni/get_scenarios` remains a list of saved scenario definitions. An SBS
row has `type: sbs_map` and `sbs_file_path`. Preserve the saved reference in row
state independently of the empty browser file chooser. Submit it in `scenarios`
JSON when no replacement File is selected. New/replacement files use
`scenarios[i][sbs_file]`; i indexes the submitted list, excluding blank rows.
A new upload takes precedence over the saved reference. No public key is removed.

Each SBS row displays `Current SBS map` using the canonical Disturbed control's
`wc-field--display` / `wc-text-display` and code-formatted basename, or `No map
uploaded.`. Render names as text, never HTML. The file chooser shows the pending
replacement; it does not relabel the accepted map before success. Successful
submission reloads accepted definitions through the normal reader. Validation
and precommit failures leave the accepted display and association intact. An
enqueue failure or transport timeout may follow a successful state commit;
reconcile through the normal reader without claiming the save was rolled back.
Reconciliation MUST preserve the original submission error/status message. Removing or changing a row's type
must not transfer its saved reference to another scenario. Ordinary reload and
module remount must produce the same accepted state.

## Saved association and two-location resolution

A request without a new file must select an exact `sbs_file_path` in the project's
saved SBS definitions. Resolve that definition, not the current request index and
not arbitrary client paths. Existing public scenario naming remains unchanged.
Resolve the saved staged file under `omni/_limbo` first. Numeric legacy directories
remain supported. New uploads use a unique staging directory under `_limbo` so
replacement or row movement cannot overwrite another accepted input.

A persisted old absolute staging prefix after a fork/restore may be mapped to the
current project's `_limbo` suffix, using only the server-owned definition. Never
read the original project. Reject traversal and invalid staging layouts. The
same exact association determines the corresponding scenario project through the
existing scenario-name function; do not scan sibling projects or guess by name.
If distinct saved references map to the same child (including equal basenames),
child recovery is ambiguous and MUST fail with replacement guidance. Exact
staged-source selection remains supported; this does not rename scenarios.

If the associated staged file is absent, resolve the associated map at
`_pups/omni/scenarios/<existing-scenario-name>/disturbed/<saved-basename>`.
Apply existing containment and raster validation. Missing historical receipts
alone do not require re-upload. A present invalid, symlinked, or unreadable source
must fail explicitly instead of falling through to an older copy.

Before accepting input for execution, restore an absent staged source from that
validated child map outside the child reset boundary. Verify copied content,
revalidate the restored file, and recheck its identity at saved-state commit.
Preserve the saved staging path where possible so unchanged input does not change
public scenario names or unnecessarily invalidate existing signatures. Do not
point execution at a child file that reset will remove. Existing execution guards
continue to detect changed selection or changed bytes after submission.

## Failures, compatibility, and cleanup

An absent reference or missing file in both locations requires an actionable
replacement message. Unknown/cross-project references, escapes, ambiguous saved
associations, and invalid rasters fail before accepted scenario mutation/enqueue.
Use existing canonical 4xx responses; retain the old accepted definitions and map
on validation/precommit replacement failures. Validate all requested rasters before publishing uploads.
Recheck that the selected saved definitions remain current under the existing
NoDb commit lock. Do not add a new lock protocol.

Existing old/new projects use the same resolution rule without migration or new
receipt schemas. Valid legacy definitions lacking content receipts may supply
fresh execution input; this does not manufacture historical proof or grant an
output-cache hit. Programmatic direct execution retains its current freshness
rules; run admission makes the staged input available before direct/RQ execution.
Batch template input saves use the same admission behavior without queuing.
Archive-backed roots retain their existing restore requirements; restored/forked
projects use only their own files. Existing scenario/project deletion owns cleanup;
no orphan sweep is introduced. Unreferenced failed-request staging files cannot
be selected by client path alone.

## Regression obligations and rationale

Scoped evidence must cover saved reload/resubmit, pending and consumed sources,
legacy definitions without receipts, dependency-triggered rerun, same-name changed
bytes, invalid replacement preservation, multiple SBS rows and blank/deleted rows,
type changes, current filenames, missing/hostile references, and restored/forked
paths. Exercise real raster validation and copy boundaries as well as browser
serialization. Verify generated execution inputs and outputs for the rerun case.

The operator requires reuse of the existing map in `_limbo` or its corresponding
scenario project and a familiar filename display. Keeping one resolution rule
for old and new projects avoids unnecessary re-uploads and migration complexity.
