# Run-sync failure diagnostics

Conformance repair (2026-09-09): the [shared controller contract's Job hints](../ui-docs/controller-contract.md#job-hints)
section requires preserving the current job link. Run-sync omitted the hint
adapter. Its aria2 exception also retained only the last 50 output lines, allowing
successful result rows to displace the error. Restore the hint wiring and retain
error diagnostics separately without changing sync success/failure semantics or
the RQ error envelope. Regression checks cover an early error followed by many
successful rows, successful subprocess completion, and the rendered job hint.

The Sync status panel retains the submitted job ID link after failure. Open that
link for RQ details. Download failures include aria2 error/cause lines ahead of
the final output tail; the retained diagnostic buffer is bounded to 50 lines.
This is not a complete download log. A nonzero aria2 exit still fails the sync
before verification and registration, even when the final rows say `OK`.
This diagnostic repair does not recover diagnostics already discarded by earlier
jobs. The subsequent [replacement contract](../schemas/run-sync-contract.md)
changes retries: listed partial files and resume metadata are cleared, and
checksum-free source manifests refresh all listed files. Unlisted files remain.

Validation: seven focused Python checks and the complete 835-test frontend suite
passed. The failure-transition regression additionally uses the real shared
job-hint renderer and confirms the link remains visible after failure. Controller
bundles were rebuilt through `wctl run-python`. Independent correctness review
found no major issues; retaining only 50 matching diagnostics is an acknowledged
limit. No source-server request or run retry was performed for validation.

Full Python sanity gate: `wctl run-pytest tests --maxfail=1` completed with
8038 passed and 72 skipped. Frontend lint, documentation lint, diff whitespace,
and changed broad-exception checks also passed.
