# Implement the Runs TTL deletion catalog

This ExecPlan is a living document. Maintain it in accordance with
`docs/prompt_templates/codex_exec_plans.md`.

## Purpose / Big Picture

After this work, a signed-in user can tell from the Runs table when an active
project is due for TTL deletion and can open a focused explanation. A run whose
TTL deletion is disabled instead retains its last-modified timestamp, so the UI
does not imply it will be deleted.

## Progress

- [x] (2026-07-21 22:15 UTC) Inspected catalog, TTL metadata, Usersum routing,
  and focused test seams.
- [x] (2026-07-21 22:15 UTC) Drafted REM-02, its decision checkpoint, security
  triage, and canonical UI contract.
- [x] (2026-07-21 22:55 UTC) Obtain post-fix confirmation from two independent
  ratification reviewers and commit GOV-00A-M1B ancestor
  `d3380287ca706360879240c3d203c5e7cc2be9ef`.
- [ ] Add read-only TTL metadata to catalog rows and render the two states.
- [ ] Publish Usersum content, update its manifest/index, and add regressions.
- [ ] Run validation, final reviews, disposition, and closeout.

## Surprises & Discoveries

- Observation: TTL state has a durable `policy` and `expires_at`, but catalog
  row construction currently returns only `last_modified`.
  Evidence: `wepppy/weppcloud/utils/run_ttl.py` and
  `wepppy/weppcloud/routes/user.py`.

## Decision Log

- Decision: add the nullable `ttl_deletion_at` presentation field to every
  existing catalog row rather than a new catalog endpoint or database column.
  Rationale: TTL remains filesystem-backed; the existing endpoint already
  builds per-run metadata, and additive fields preserve compatibility.
  Date/Author: 2026-07-21 / Codex.

## Outcomes & Retrospective

Pending implementation.

## Context and Orientation

`wepppy/weppcloud/routes/user.py` owns `/runs/catalog`. It selects runs under
the caller's existing owner/admin scope, then builds metadata from each run
directory. `wepppy/weppcloud/utils/run_ttl.py` reads a JSON `TTL` file in that
directory; `read_ttl_state` is the non-mutating API. `runs2.html` fetches the
catalog and creates each row with DOM APIs. Usersum resolves a manifest doc-id
to rendered Markdown under `/usersum/doc/<doc_id>`.

## Plan of Work

First complete independent contract and security review, post-fix confirmation,
and commit the reviewed GOV-00A-M1B checkpoint separately. Then add a small
helper in `user.py` that reads TTL state only after a row is authorized and adds
`ttl_deletion_at`, either `null` or a normalized UTC ISO-8601 string ending in
`Z`. Only `rolling_90d` with a timezone-aware ISO-8601 expiry is active. Missing
files, malformed JSON, non-mapping state, unknown/non-string policy, and
missing/null/invalid expiry all return `null` without mutation or a
catalog failure. Adjust the client row builder to make one lifecycle cell: an
active expiry has exact `TTL Deletion:` text and a Jinja server-generated
same-origin link; all other states use exact `Last Modified:` text. Preserve the
database last-modified sorting contract.

Add `run-ttl-deletion.md`, its public-user manifest item, navigation/search
description, and validate the generated index. Add focused tests for helper state mapping,
unselected-row no-read ordering, selected-admin read behavior, template
prefix/link/text-node behavior, and normal-user/privileged Usersum resolution.
Rebuild the named Usersum index only through the documented Usersum tool; do not
hand-edit it.

## Concrete Steps

From `/home/workdir/wepppy`, run:

    wctl run-pytest tests/weppcloud/routes/test_user_meta_boundaries.py tests/weppcloud/routes/test_user_runs_admin_scope.py tests/weppcloud/routes/test_usersum_bp.py tests/weppcloud/test_usersum_template_wiring.py
    wctl run-npm lint
    wctl run-npm test
    wctl doc-lint --path docs/work-packages/20260721_runs_ttl_deletion_catalog
    python3 tools/usersum_docs_tool.py build-index --write --require-vendor-files
    python3 tools/check_broad_exceptions.py --enforce-changed --base-ref <contract-ancestor>
    git diff --check

## Validation and Acceptance

Focused tests must prove active rolling TTL renders an expiry plus safe link,
and a disabled TTL state renders last modified only. A Usersum request to
`/usersum/doc/usersum.weppcloud.run_ttl_deletion` must return 200 and include
the policy explanation for normal and privileged users. Existing non-admin/admin
catalog scope tests must still pass, including a sentinel unselected run whose
TTL reader must never run. No authorization, mutation, queue, or TTL computation
behavior may change.

## Idempotence and Recovery

`read_ttl_state` already maps expected `OSError` and `json.JSONDecodeError` file
failures to `None`; the catalog helper must not add a broad exception handler.
It may handle only `TypeError` and `ValueError` from its own timestamp parsing.
Rebuilding the Usersum index is a repeatable validation step, but the root
AGENTS instruction requires ignoring any resulting dirty generated index unless
the user separately authorizes modifying it. The implementation can be reverted by
reverting its post-ancestor commit; it creates no database migration or run-tree
mutation.
