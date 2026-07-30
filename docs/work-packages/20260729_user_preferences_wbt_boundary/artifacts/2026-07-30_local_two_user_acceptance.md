# Local two-user acceptance

**Date**: 2026-07-30 UTC

**Environment**: fully restarted local development stack exposed through
`https://wc.bearhive.duckdns.org`.

**Result**: PASS after receipt-bound operator cleanup.

## Corrected procedure and receipts

The initial `livelong-blouse` evidence was rejected by both post-acceptance
reviews because cleanup and coverage claims were incomplete. Those FAIL
artifacts remain authoritative for the rejected fingerprint. The corrected
acceptance stopped both RQ workers, proved the two exact disposable emails
absent, and created Users 312 and 313 with only the existing User role
(role 1). Controlled Flask-Security session materialization was used because
this local deployment intentionally disables password login in favor of
external OAuth. Each resulting server-side session was verified through the
real Profile route and recorded for exact Redis cleanup.

User 312 created run `inflammatory-bilberry` (Run row 1394) with
`disturbed9002_wbt`. The only added sharing receipt was `(user_id=313,
run_id=1394)`. The real preference POST contract saved:

- User 312: SI and Stop with an Error;
- User 313: English and Warn and Continue.

Both users loaded the same run page. The server rendered SI for User 312 and
English for User 313. Auto used the project Unitizer, and the accountless
resolver also returned the project Unitizer. The durable `unitizer.nodb`
SHA-256 stayed:

```text
a9cbdbf93b9ec736783b6670860bb008718c340004aa4e8678d268f27d82655a
```

Four real WBT roots were submitted and inspected while workers were stopped:

```text
f8aac1b4-793d-48d2-ae75-886fcba96bb4
2035fa60-887d-4994-977f-297902f189ce
57cfa067-def5-4a24-b044-b22c2f0a9f2d
b95ad59c-93af-482a-a271-a5b462dc0c2b
```

They proved User 312 `error`, User 313 `warn`, User 312 Auto/config `warn`,
and service/accountless project fallback `warn`. The first three roots carried
the expected private initiating-user snapshots; the service root carried
neither a user snapshot nor a child policy argument. Public jobinfo redacted
all private snapshots. The run's durable boundary fields remained
`["warn", "warn"]`.

The public-session HTTP gate remains covered by route contract tests rather
than this canary: a plain anonymous request is not equivalent to a
CAP-authorized public session. The corrected harness no longer makes that
invalid substitution.

## Cleanup and postcondition

The harness removed the four exact jobs and tail, two exact server-side
sessions, the exact WD-cache key, sharing and role receipts, Run row,
preference rows, and Users. User, preference, role-association, and
run-association counts returned exactly to their preflight values:

```text
users=10 preferences=1 roles_users=11 runs_users=226
```

Independent receipt checks returned zero for Users 312/313, their preferences,
role/run associations, Run 1394, all four job hashes, and the mutation tail.
The first post-review scan found exact stale WD-cache keys for six disposable
acceptance attempts. The operator deleted only those six named DB-11 keys and
verified each absent; the harness now deletes and asserts its exact run key.
NFS retained open `.nfs` handles for the disposable directory, so the harness
reported `checks_passed_cleanup_pending` rather than PASS. The operator
restarted only WEPPcloud and rq-engine, removed exactly
`/wc1/runs/in/inflammatory-bilberry`, and confirmed both that path and
`/wc1/runs/in/.inflammatory-bilberry` absent. Workers were then restarted and
the complete local stack returned healthy.

## Failure containment changes

The acceptance cycle exposed and closed three harness/product-boundary gaps:

- the Create token now requires an exact positive integer `current_user.id`
  and cannot fall back to email or Flask-Security's `fs_uniquifier`;
- failed Create cleanup now closes run-scoped NoDb instances, purges and
  verifies exact DB-0/11/13 state, then removes only the canonical generated
  directory; any failure retains the existing public `error_id` and emits one
  correlated internal record containing that `error_id` and generated run ID;
- the harness records job IDs incrementally, emits no PASS before cleanup,
  deletes exact server-side sessions and the run access log, reports NFS
  cleanup as pending, and records before/after counts plus all non-secret
  receipts.

No Forest or production host was touched during local acceptance.

## Strict-cleanup rerun

The post-remediation canary used Users 341/342, Run 1404
(`pain-free-prospectus`), and jobs
`71592eb7-c198-469f-92c8-4f75a34725f9`,
`2141b08b-7ce8-420a-8691-716ce5acbf46`,
`3ea9e673-9227-4d08-bc14-cbea5e3708ac`, and
`98a367bf-9ec7-4518-9412-bcf9f46c63a9`. It repeated the distinct SI/English
presentation, Auto/project fallback, user `error`/`warn` WBT snapshots,
private-snapshot redaction, byte-stable Unitizer, and unchanged durable WBT
fields. SQL counts returned exactly to the pre-canary values.

The strict cleanup postconditions found zero exact state in Redis DB
0/2/9/11/13/14/15. NFS retained 13 zero-length `.nfs*` handles, so the harness
correctly emitted `checks_passed_cleanup_pending` with its complete
non-secret receipt and no PASS. After restarting only WEPPcloud and rq-engine,
the handles disappeared; the operator removed the now-empty exact directory,
verified both the run directory and access-log path absent, and restarted both
workers. This is an observable NFS handle-lifetime limitation, not silent
Redis or database residue.
