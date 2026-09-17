# After-restart Geneva/archive security acceptance

**PASS for this bounded runtime operation, including the later live browse and
failed-artifact downloads below. Profile ownership stays separate; this does not
close the package security gate.**
Reviewer: `freshness_security`, 2026-09-17. No production or test code was changed.

## Restart and execution evidence

The retained `runtime_restart_verification.json` names source revision
`de3a1eba03ba2a0a09beef84e7f3a768d34690fe` and image
`sha256:00a3e43a88a5c9079a7e58a8423432d69f22b7b09c0a9288078b67abbca1d3f8`.
Independent readback confirms all16 listed services were recreated, running on
that image with their prior users/groups and mounts; every reported health check
was healthy. The execution used the recreated `weppcloud` container
`34145e0697ac58ab5a1ec2aa2f77cef3731062a99bcb06968df010a5977f5e72`.

```text
wctl exec weppcloud python docs/work-packages/20260916_file_dependency_freshness/artifacts/runtime_archive_acceptance.py --restart-evidence docs/work-packages/20260916_file_dependency_freshness/artifacts/runtime_restart_verification.json
```

The command exited0 on its first execution. Evidence:

- [Raw operation log](runtime_archive_acceptance_after_restart_initial.log).
- [Complete manifest](runtime_archive_acceptance_3a8be19a8e1e.json), also retained
  at the disposable batch root as `acceptance-manifest.json`.
- [Prepared driver](runtime_archive_acceptance.py) and
  [operation boundary](runtime_archive_acceptance_requirements.md).

The new project is
`/wc1/batch/qa-freshness-archive-3a8be19a8e1e/runs/archive`. Actual effective
UID1000/GID993, supplementary groups `[993]`, umask0022. No root override,
credential access, existing project reset, live queue submission or restart was
performed by this driver. Other native work may have overlapped; elapsed time is
not performance evidence.

## Actual results

Native Geneva geometry produced one feature; native aligned SBS pixels were
`[[3, 3], [3, 3]]`. Both successful attempts retained complete status. A third
deliberately failed `_Attempt` retained its partial `failed.geojson` and failed
status, while accepted geometry bytes stayed unchanged.

Canonical `archive_rq` and `restore_archive_rq` used real filesystem/ZIP and
project lifecycle guards. The existing `ArchiveRuntime` supplied only disposable
job/status/path transport and empty lock/cache fixtures; this was not a live RQ
job. All **10 files and7 directories** matched their recorded bytes/modes in the
ZIP and after restoration. Attempt root and all three leaves remained0700;
status files remained0600. The failed candidate remained present. Geometry
reused the accepted artifact after restore without creating a fourth attempt.

The archive is
`archives/security-runtime-3a8be19a8e1e.20260917T080441Z.zip`, SHA-256
`6c5e96d033bdbff6fe62f822f77edcad5668d67bcce4ba131a6366befd481382`.
The driver bound the restart-record hash and four exercised production-module
hashes; all module hashes stayed unchanged through the operation.

Ordinary `get_page_entries` listings exposed every expected record before and
after restore, without listing overrides or fabricated manifest entries.
Actual ASGI file responses returned200 and delivered each recorded SHA. These
are helper visibility/delivery controls; they do not prove live authentication.

Parent's actual HTTP verification target:

```text
/weppcloud/batch/qa-freshness-archive-3a8be19a8e1e/browse/runs/archive/
```

The failed evidence is under
`geneva/cache_attempts/fe140f898bf74c8cb65b58bdff9e1d4a/`; verify its status and
candidate through the normal authorized browse/download paths. Accepted files
and archive must remain available too. Login redirects or404 are not acceptance.

## Remaining gates

No profile seed roots were supplied because actual capture had not yet run.
Their read-only receipt check can follow actual capture/promotion; project ZIP
coverage must not be claimed for external profile storage. Canonical profile
HTTP auth outcome, the separately authorized bearer-session verification,
live browsing/download authorization, other operation-matrix workflows and
final runtime security consolidation remain pending.

The final broad Python log now independently reads **8924 passed,99 skipped**
in1192.22s. That outcome is separate from this native/permissions proof. Earlier
archive failure evidence remains intact in the implementation review; this
successful operation does not rewrite those original observations.

## Follow-up: live HTTP and transport isolation

Parent's actual authenticated
[browse response](runtime_archive_helper_public_browse.json) is200 with the
expected archive/Geneva/source listing. Both failed-attempt files have actual
[download responses](runtime_archive_helper_public_downloads.json) of200:
status.json268bytes and failed.geojson30bytes, with SHA exactly matching each
restored private-mode source. This closes the stated live listing/failed-record
delivery check; it does not exercise every role/denial or a live archive RQ job.

The generic filesystem leaf `archive` did not select a shared RedisPrep owner.
Source inspection of the executed driver confirms the explicit
`ArchiveRuntime.get_prep_from_runid` returnsNone for initial and finally cleanup
calls, lock-status/cache-clear callbacks return empty fixtures, and status
publication appends to a local list. Both canonical functions require this
runtime; neither instantiates RedisPrep. The passed run ID is the unique
`security-runtime-3a8be19a8e1e`. Geneva uses a `SimpleNamespace` owner with the
actual artifact/native helpers, not NoDb hydration. The real lifecycle guard
uses a file flock at this disposable root and returns from recovery when its
journal is absent. Thus these executed paths did not hydrate/write a shared
RedisPrep `archive` key. This is source-bound transport isolation, not a Redis
traffic audit or evidence about live batch/RQ leaf namespace behavior.

The subsequent read-only draft/promoted profile checks and actual HTTP playback
have their separate [S02 disposition](runtime_profile_security_review.md).
Their records were never moved into this project or claimed as ZIP members.
