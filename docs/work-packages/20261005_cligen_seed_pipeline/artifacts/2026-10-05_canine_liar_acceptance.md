# `canine-liar` CLIGEN Seed Acceptance

## Scope

- Source run: `canine-liar` (`disturbed9002_wbt`)
- Disposable build run: `cligen-seed-e2e-20261005-a`
- Source-invariance control fork: `cligen-seed-e2e-20261005-b`
- Contract checkpoint: `514a7da28795782ad662beca84239f172971d113`
- Explicit seed: `24680`
- Fork flags: `undisturbify=false`, `skip_wepp_runs_output=true`, and
  `skip_omni_scenarios_contrasts=true`

Both destinations were created through the authenticated rq-engine fork route,
which enqueued the canonical `fork_rq` worker. The normalized Omni `scenarios`
and `contrasts` directories in the control fork were both empty.

## Request-to-Executable Evidence

The authenticated build request selected one-year, single-spatial-mode vanilla
CLIGEN and submitted `cligen_seed: 24680`. RQ job
`72995cb3-d1da-4c11-9a8c-6d4d87e41e46` retained the exact `build_payload` in
job metadata. Reloading `Climate` from the destination NoDb returned
`cligen_seed == 24680`.

The generated `climate/cligen_wepp.log` recorded:

```text
cmd: /workdir/wepppy/wepppy/climates/cligen/bin/cligen532 -iid106388.par -r24680
```

The same log verified the binary and sidecar identities:

- CLIGEN binary SHA-256:
  `119ba1de5bc48757901224c8d6e91022a91bf255a45043a98579199e681aaddc`
- Sidecar SHA-256:
  `c2ce9caa4d4a82f368eea66bb3ea5b6ae2b833920b893d9d6deef974e2f6cf06`
- Release label: `5.323-k10.1`
- Identity status: `verified`

`ClimateFile.as_dataframe()` parsed the fresh output as 365 rows with the
expected 13 daily climate columns. Its SHA-256 was:

```text
9ef33007a59a1ba1707e943d08702b2586180d6b9541c2850d6f72a1b41b3888
```

A second authenticated request with the same payload ran as RQ job
`1df6975d-335c-4987-b396-b207785b20df`. The regenerated `wepp.cli` had the same
SHA-256, proving byte-identical deterministic replay at the actual binary
boundary.

## Source-Run Integrity and Fork Bookkeeping

The initial complete source-file content/path manifest was:

```text
files=3419
aggregate_sha256=acce8a5fb4e3f93aa2d6e5382a13a8034c76558598416212fd15bcbe174403a5
symlink_manifest_sha256=77264ff1f65ddd29c30b8ff180498f7bb95c3c6ce8f3dd6e4f4a244cee06ed1d
```

The supported fork route intentionally writes source orchestration bookkeeping:
it stores the latest `rq:fork_rq` identifier in `redisprep.dump` and appends job
completion to `rq.log`. Consequently, requiring the entire source directory to
remain byte-identical was incompatible with the approved canonical workflow.
No climate or model input/output in `canine-liar` was rebuilt or edited.

To prove that boundary directly, a second normalized fork was run while hashing
every source file except those two documented bookkeeping files immediately
before and after the fork. Both manifests were identical:

```text
model_content_aggregate_sha256=2a90b08db58a98960d677cb0318e76806b78d3039df202afb6326993cdddee4a
```

The complete manifest changed only as expected for source-side fork
bookkeeping. This is the correct non-destructive acceptance boundary for the
supported fork workflow.

## Result

Pass. The evidence connects authenticated request intent, persisted NoDb state,
queued metadata replay, `Climate.build`, the exact verified executable command,
parseable generated output, and deterministic replay. Mutation of climate and
model artifacts was confined to the disposable build fork.

Cleanup jobs `a6090ff0-3ed7-48fc-9af8-362f03029e44` and
`5e142c69-6ffb-450b-b725-69021b5eb3af` completed through the canonical
`delete_run_rq` path. They removed the disposable project contents and database
records. NFS retained only deletion-queued TTL stubs (and one transient `.nfs`
handle), reducing the two destinations from roughly 138 MB combined to less
than 85 KB pending normal garbage collection.
