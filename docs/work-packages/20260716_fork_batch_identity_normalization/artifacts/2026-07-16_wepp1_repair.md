# wepp1 Repair Evidence - `subsequent-hotbed`

## Scope and Identity

- Host: `wepp1`
- Host run root: `/geodata/wc1/runs/su/subsequent-hotbed`
- Container run root: `/wc1/runs/su/subsequent-hotbed`
- Configuration: `disturbed9002-wbt-mofe`
- Expected copied batch: `nasa-roses-202606-psbs`
- Inspection window: 2026-07-16 10:15-10:31 PDT

The host and container path existed, the `weppcloud`, `rq-engine`, `rq-worker`,
and `rq-worker-batch` services were running, and `weppcloud` was healthy. The
container user was `roger` (`uid=1002`, `gid=130`). No filesystem lock files or
active Redis locks were present.

## Baseline

The ash route returned `Set ash inputs for batch processing`. Thirteen root
NoDb files contained `_run_group: "batch"` and `_group_name:
"nasa-roses-202606-psbs"`. Active `run_metadata.json` identified source leaf
`batch;;nasa-roses-202606-psbs;;WA-10`.

The pre-repair content hash over `_pups/**/*.nodb` was:

    75c592f1a78a1d526799ed1aa8ff2b600535a962c9000f6e31ec81e41beee14d

## Script and Dry Run

The locally tested script was copied to
`wepp1:/tmp/repair_forked_run_identity.py`. The applied script checksum matched
on both hosts:

    aa1cc672ebfe6b94e759ebd7d599a631b892d8f7a63018c0b9ce9e30417e8541

The dry-run reported exactly 13 root controllers and one copied batch metadata
file, all under the expected batch name. It did not create a backup or write.

## Apply Result

The script ran inside `docker-weppcloud-1` with:

    /opt/venv/bin/python - /wc1/runs/su/subsequent-hotbed \
      --runid subsequent-hotbed \
      --expected-batch-name nasa-roses-202606-psbs \
      --apply --clear-cache

Result:

- Root controller identities cleared: 13.
- Active copied `run_metadata.json` removed: yes.
- NoDb cache entries invalidated: 15.
- Backup:
  `/wc1/runs/su/subsequent-hotbed/_repair_backups/forked_batch_identity_20260716T173025Z`
- Backup manifest status: `complete`.
- Backed-up `run_metadata.json`: present.

The broad existing cache helper also invalidated two cache-only entries reached
through `_pups` symlinks into the source batch. No source files or persisted
source state changed. The repository CLI was immediately narrowed to clear only
the root NoDb files it modified, with an exact regression test.

## Acceptance Verification

At 2026-07-16 10:30:59 PDT:

- Every root `.nodb` reported null/absent `_run_group` and `_group_name`.
- Active `run_metadata.json` was absent.
- The `_pups/**/*.nodb` content hash remained exactly
  `75c592f1a78a1d526799ed1aa8ff2b600535a962c9000f6e31ec81e41beee14d`.
- Fresh `Ash.getInstance(...)` returned:

      {'run_group': None, 'group_name': None,
       'runid': 'subsequent-hotbed', 'batch_blocked': False}

- A repeat dry-run reported zero controller or metadata changes.

After review hardening, the final root-scoped script was recopied to `/tmp` at
2026-07-16 10:56:41 PDT. Local and `wepp1` checksums matched:

    6c2b9aa75571dcae2d0fe820906bc7670bec1e4fa137409942bb12bf87eb8323

Its production dry-run again reported zero controller or metadata changes. WATAR was
not submitted automatically because Alex's saved UI inputs remain the authoritative
run choices.
