# Tests in isolated worktrees

Use `wctl run-pytest-worktree` instead of ad hoc Compose mount commands. It uses
an ephemeral `weppcloud` container with the installed preset's configuration,
mounts the candidate source, verifies the existing checkout nonce, and does not
start dependencies, publish ports, rebuild images or recreate shared services.
Run from the candidate worktree; `--checkout` selects it explicitly. Keep the
installed preset pointed at the configured development checkout. `--project-dir`
selects the Compose/environment project, not a substitute for `--checkout`.

```bash
# Focused tooling tests: no browser/native/database prerequisites needed.
wctl run-pytest-worktree --profile python -- tools/wctl2/tests -q

# Default broad preflight; report all missing prerequisites before collection.
wctl run-pytest-worktree --preflight-only -- tests

# Reuse compatible installed assets explicitly; no dependency installation.
wctl run-pytest-worktree --checkout /path/to/candidate \
  --runtime-root /path/to/dependency-checkout \
  --shape-parser /path/to/shape_parser_cli \
  --geoparquet-parser /path/to/geoparquet_parser_cli \
  -- tests --maxfail=1
```

The last two options require an adjacent `<binary>.json` provenance sidecar.
Omit them if the existing image or candidate already supplies valid parsers.
The validator checks executable identity, version, complete Rust source inventory
and source hashes against the candidate. A matching binary hash alone is not
source compatibility. Use the canonical parser build workflow when sources differ;
do not copy an arbitrary binary or silently bypass provenance checks.

`--runtime-root` borrows only `static-src/node_modules`, `.playwright-browsers`
and dependency manifests, mounted read-only. Both package manifests must match
candidate bytes, and installed package metadata must match the lock. Chromium
must actually launch and read a test page. This validates readiness, not an
attestation that every installed dependency byte is trustworthy. Use only a
trusted local dependency checkout. It does not borrow generated controller code:
the runner renders `controllers-gl.js` from the candidate builder and templates.
Without a donor, prepare candidate dependencies through `wctl --project-dir
/path/to/candidate run-npm ci` and install the matching Playwright Chromium with
`PLAYWRIGHT_BROWSERS_PATH` set to the candidate's `static-src/.playwright-browsers`.
For example:

```bash
wctl --project-dir /path/to/candidate run-npm ci
PLAYWRIGHT_BROWSERS_PATH=/path/to/candidate/wepppy/weppcloud/static-src/.playwright-browsers \
  wctl --project-dir /path/to/candidate run-npm exec -- playwright install chromium
```

Preparation is explicit; the test command never installs packages.

## Profiles and results

Default `broad` checks controller generation, Node/Chromium, both native parsers
and PostgreSQL model-column compatibility. Explicit `browser`, `native` and
`database` profiles select those respective prerequisites. `python` only verifies
checkout/source integrity. Narrow profiles are for selected test paths; bare
`tests` or `.` requires `broad`. Profiles do not skip or filter pytest tests and
are not substitutes for the runtime requirements of the selected tests.

The database check uses a read-only transaction and reports missing tables and
columns. It never creates a schema, runs migrations or changes permissions. A
stale schema such as missing `user.account_kind` blocks execution with repair
instructions. Provision an isolated integration database using canonical
migrations and the established environment configuration, then rerun preflight.
Column readiness does not prove constraints, migration correctness or test behavior.

Every invocation reserves a unique `.wctl-test-runs/<id>/receipt.json` in the
candidate. It records prerequisites, runtime identities, actual UID/GID/groups,
test arguments, pytest exit status and before/after source fingerprints. A
preflight-only success means **ready**, not **tests passed**. Missing prerequisites
exit 2 without starting pytest. Source mutation exits 3 even if pytest returns 0.
Interrupted invocations retain an incomplete receipt; they are not passes.
Receipts are ignored by Git; copy selected evidence into a work package to retain it.

The runner owns a short unique `/tmp/wt-*` basetemp, avoiding AF_UNIX path-length
failures. Container scratch disappears on exit; explicitly select candidate paths
for pytest JUnit/output artifacts you need to retain. Source fingerprints include
tracked and untracked nonignored executable/config/template files, additions,
deletions and symlink targets. They detect before/after differences, not temporary
writes restored within a run, and are not a concurrency lock. Freeze source while
testing. Recorded runtime files are rehashed after execution; changes also fail the run.
The runner never resets or silently repairs a test-written source file.

## Known boundaries

A worktree isolates source, not shared Redis workers, databases or network services.
Integration tests must use private queues and disposable schemas/run directories.
Do not treat a copied checkout or mounted ignored assets as a full production
identity simulation. Baseline test-fixture defects and load-sensitive performance
failures remain failures after prerequisites pass. Capture and investigate them;
do not loosen thresholds, skip failures or claim a green suite from preflight.

The existing `run-pytest` and sharded commands retain their shared-container
behavior and fail on a checkout mismatch. Use this command when working in a
linked checkout; do not remount another task's running stack.
