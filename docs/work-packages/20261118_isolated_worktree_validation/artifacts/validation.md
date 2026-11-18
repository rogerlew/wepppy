# Worktree validation evidence

All runs use the task-local canonical wctl shim at
`/tmp/wctl-worktree-validation`, installed with `WCTL_SYMLINK_PATH` so the shared
CLI is unchanged. Compose/environment project: `/home/workdir/wepppy`.
Candidate: `/home/workdir/wepppy-worktree-validation`. The branch starts at
`0aaabd9e8`; exact dirty/untracked candidate source hashes are retained per run.

## Results

| Run | Result |
| --- | --- |
| Full wctl suite, final command/environment handling | 93 passed, 4.08 seconds |
| Tooling plus repaired profile fixture | 136 passed, 29.76 seconds |
| Complete native shape-converter suite | 315 passed, 34.95 seconds |
| Complete unitizer, run-table and catalog-reader modules | 24 passed, 37.02 seconds |
| Fresh broad preflight without runtime donors | Browser, two parsers and schema reported together; no pytest |
| Final broad attempt with compatible runtime donors | Assets ready; seven missing user columns reject before pytest, exit 2 |

Every successful run has unchanged before/after source fingerprints. Runs with
runtime-file monitoring also have no changed recorded runtime files. Earlier
receipts identify the exact implementation at execution rather than being
rewritten to claim later receipt-progress and CLI-context edits existed then.
The final tooling suite covers those later changes; final broad preflight
revalidates all real native/browser prerequisites with the final implementation.

The missing schema columns are `account_kind`, `contact_email`,
`local_credential_state`, `mailbox_verified_at`, `mailbox_verified_email`,
`verification_nonce` and `verification_sent_at`. Read-only inspection did not
migrate or create anything. This full-suite attempt is **blocked before pytest**,
not a passing broad regression run. No load-sensitive latency assertion was
changed or declared resolved.

## Reproduction

The canonical command is documented in tools/wctl2/docs/worktree-tests.md. These
runs explicitly supplied the primary checkout for Node/Chromium dependencies,
its existing shape parser, and the existing provenance-verified GeoParquet binary
retained during the Roads investigation. No application dependency installation,
parser build, shared stack remount, database migration or live worker stop occurred.
The canonical CLI installer bootstrapped its existing Typer/Click dependencies
only in the task worktree.

Exact commands are in compressed logs. Unique receipts and logs are retained in
`evidence/`; validation_receipt.json records original/decompressed SHA-256 values.
Every compressed file was roundtrip verified. The receipts expose prerequisites,
actual user/group identity, source manifests, native/Node/controller hashes,
status and pytest arguments. They distinguish ready, running, failed, passed,
not-ready and integrity failures. CLI tests exercise interruption, missing paths,
mount-field injection, foreign Git settings, stale locks/source and source/runtime
mutation without concealing the resulting files.

Documentation and source formatting gates are recorded at handoff. Correctness
and security reviews are primary-integrator self-reviews, not independent agent
or human approvals. Source changes remain local and unmerged.

Final gates: all 14 changed Markdown files pass doc lint; root AGENTS remains
160 lines; whitespace checks pass. Spelling previews only flag preexisting
`axe` and `--warmup` identifiers, which are preserved. Broad-exception enforcement
explicitly scans all six changed Python files and reports zero broad catches.
Observe-only repository telemetry completed; its default scope has no changed
production files here. Direct Radon measurements in quality.json cover the two
new tooling modules: 82/212 SLOC, maximum spans 39/58 lines, maximum CC 7/23.

The final caller-selection regression initially exposed an older test assumption
that Compose project selection also selected source. The test now explicitly
selects its candidate; a separate regression verifies caller selection despite a
different Compose project. The unsuccessful attempt is retained alongside the
88-pass replay. Actual final invocation omitted --checkout and used the caller's
live task worktree, with unchanged source and runtime checks.

The final profile guard also normalizes common full-suite aliases (`./tests`,
`tests/`, `tests/../tests`, `.`); these cannot accidentally use a narrow profile.
All 93 tooling cases pass after adding that coverage. The shared wctl symlink
still resolves to /home/workdir/wepppy/wctl/wctl.sh.
