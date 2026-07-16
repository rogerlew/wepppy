# Forest Acceptance - AgFields Watershed Parent Job

## Scope

Authenticated local-forest acceptance uses run
`/wc1/runs/sa/sacral-self-discipline` with configuration
`disturbed9002_wbt`. Bearer credentials were issued for the acceptance session
and were neither printed nor persisted in this artifact.

## Submission Evidence

- Submitted at approximately 2026-07-16 00:01 UTC through
  `POST /api/runs/sacral-self-discipline/disturbed9002_wbt/agfields/run-watershed`
  with `scheme=all`.
- HTTP response: `202`.
- Suite parent: `32845fca-6e3d-4906-a77b-94665a58ae94`.
- Concept 1 child: `1c246668-1d95-4949-98e7-310da9452d43`.
- Concept 2 child: `c6c551db-08d3-4366-8ecd-ba36c812b95c`.
- Hybrid child: `767a0951-5727-41a3-8add-c3ce2931cdbd`.
- Finalizer: `fcf9a476-d4ce-42d6-b46e-e521b352fa4a`.

## Initial Tree Verification

- Parent job info exposed ordered groups `0`, `1`, `2`, and `3` for Concept 1,
  Concept 2, hybrid, and the finalizer respectively.
- Concept 1 entered `started`; Concept 2, hybrid, and the finalizer were
  `deferred`.
- The physical dispatch parent finished after child registration while
  recursive `/jobstatus/{parent}` correctly remained `started` at 1/5.
- The AgFields state endpoint exposed the suite parent and all three named
  scheme IDs.

## Terminal Verification

The suite reached terminal success at 2026-07-16 04:22:55 UTC.

- Recursive parent status: `finished`, progress 5/5 (100%), no exception.
- Group `0`, Concept 1: `finished`, 00:01:23-01:57:26 UTC, no exception.
- Group `1`, Concept 2: `finished`, 01:57:26-02:53:25 UTC, no exception.
- Group `2`, hybrid: `finished`, 02:53:25-04:22:55 UTC, no exception.
- Group `3`, finalizer: `finished`, 04:22:55 UTC, no exception.
- The finalizer started only after hybrid reached terminal state.
- The AgFields state endpoint reported no active AgFields job IDs after
  finalization and retained the suite parent plus all three scheme IDs.
- Worker logs reported `Job OK` for the parent, each scheme child, and the
  finalizer; no matching traceback or error was present.

## Fixed Output Verification

Each terminal integration summary reported `status=completed`,
`parent_count=3543`, `pass_count=3543`, `failure=null`, and nine required
resources. All 27 listed resources existed under the designated run root.

| Scheme | Summary completion (UTC) | Fixed output root |
| --- | --- | --- |
| Concept 1 | 2026-07-16 01:56:56 | `wepp/ag_fields/watershed/concept-1/` |
| Concept 2 | 2026-07-16 02:52:56 | `wepp/ag_fields/watershed/concept-2/` |
| Hybrid | 2026-07-16 04:22:17 | `wepp/ag_fields/watershed/hybrid/` |

## Verdict

Pass. The local forest acceptance demonstrated one composable parent tree,
serial scheme handoffs, non-terminal aggregation throughout active child work,
an after-all-children finalizer, and complete fixed output trees.
