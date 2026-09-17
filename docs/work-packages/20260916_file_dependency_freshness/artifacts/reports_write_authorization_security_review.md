# Report publication write-authorization follow-up

Independent security follow-up after `0f2826a25`, 2026-09-17 UTC. No production
or test edits; only disposable probes and review artifacts. This follows the
CLI contract review's distinction between inode write permission and directory
replacement permission.

Final scoped disposition: **PASS after both verified corrections below**.
RP-SI04 and RP-SI05 are closed; original before/after evidence remains retained.

## Confirmed finding

**RP-SI04 — Medium, CLOSED after the independent follow-up below: C09 atomic publication bypassed the existing target
write-access boundary.** A worker that can create/replace files in the report
cache directory can now replace a canonical landuse cache whose inode is
read-only to that same identity. Before the report wave, the actual pandas writer
raised PermissionError and kept its bytes. Current `_CacheBuild` only checks
target type, selection and mode; copying mode 0444 onto a new inode does not
preserve the original denial. This violates the canonical requirement to preserve
existing access rules. It is a concrete data-integrity/noninterference regression,
not a claim of broader cross-user or remote privilege escalation.

Required remediation: preserve the old C09 target write-authorization check with
a nondestructive write-open under the executing identity, bound to the selected
resolved target. Check before publication and preserve prior rows/proof on denial.
Do not truncate merely to check permission, rely only on mode bits or parent
permission, or add a new read requirement for write-only targets. Keep existing
symlink destination selection, effective access and atomic publication semantics.

**Do not apply this new check to C08.** The actual pre-wave native water-balance
producer already atomically replaced a 0444 target when its directory was
writable, preserving mode 0444. Current C08 does the same. Adding an inode-write
requirement to C08 would narrow established native behavior without authorization.
This is why the permission rule must be consumer-specific inside the shared
publication helper.

**RP-SI05 — Medium, CLOSED after the independent follow-up below: both report writers overwrote a read-only version
sidecar and broaden its mode.** If a present `.meta.json` requires version repair,
old C08/C09 `write_text` fails on a 0444 sidecar. New publication replaces it using
directory permission and the Parquet mode, producing mode 0644. Required repair:
preserve the sidecar's own write authorization and mode when actually changing
it, before accepted publication; a current version-1 sidecar needs no gratuitous
write. The source/Parquet may remain readable and writable in this scenario.

## Actual before/after evidence

`reports_write_authorization_probe.py/.log`: **4 passed**, 9.42 seconds.
These assertions characterize behavior, not repaired acceptance.

```text
wctl run-pytest docs/work-packages/20260916_file_dependency_freshness/artifacts/reports_write_authorization_probe.py -v -s --maxfail=1
```

Two prior report modules are exact retained `git show 7d78e9810:<path>` snapshots:
`reports_prior_hillslope_permission_snapshot.py` and
`reports_prior_landuse_permission_snapshot.py`. They are loaded under separate
package-qualified module names; their actual native/PyArrow/DuckDB paths run.
Current classes run independently against equivalent disposable real Parquet
fixtures. Only the fixture's existing controller acquisition isolation is used.
No writer, filesystem authorization, native aggregation or query is mocked.

Each case first builds a valid cache, changes its selected scientific source,
sets the ordinary version sidecar to force a rebuild in both old/new reports,
then chmods the canonical Parquet to 0444. UID is 1000, the parent is writable,
and an actual `os.open(cache, O_WRONLY)` raises PermissionError before the report
call. Per-case JSON files retain the result.

| Consumer / revision | Actual result | Prior bytes | Final mode |
| --- | --- | --- | --- |
| C08 native, `7d78e9810` | Rebuild returns successfully | Replaced | 0444 |
| C08 current | Rebuild returns `built` | Replaced | 0444 |
| C09 pandas, `7d78e9810` | PermissionError | Preserved | 0444 |
| C09 current | Rebuild returns `built` | Replaced | 0444 |

The version mismatch makes both implementations invoke their supported producer
path; it avoids comparing old C09's stale reuse bug with new content-triggered
regeneration. It does not grant permission to overwrite the read-only inode.

`reports_sidecar_authorization_probe.py/.log`: **4 passed**, 9.38 seconds. This
uses the same actual old/new producers with writable Parquet and a mismatched
0444 sidecar. Both old producers raise PermissionError and leave the sidecar
bytes/mode unchanged, although they have already rewritten the data file. Both
new producers return `built`, rewrite the sidecar and change 0444 to 0644.
Per-case `reports_sidecar_authorization_*.json` retains the observations. Its
inherited `prior_target_write_open_denied` field refers to the sidecar in this
probe; the script explicitly passes that path to `os.open`.

The old data-first failure ordering is not a required behavior to preserve. The
new atomic protocol should reject sidecar access before committing the new data,
keeping old rows and proof together on failure. This permission requirement applies
to sidecar mutation for both consumers, independently of C08's native data-file
replacement semantics.

## RP-SI04 independent fix verification

The parent added a nontruncating `os.open(target, O_WRONLY)` in `_CacheBuild.publish`
for existing C09 targets only. It precedes candidate chmod and accepted-file
replacement; C08's native behavior remains unchanged.

`reports_write_authorization_after_probe.py/.log`: **2 current cases passed**,
9.15 seconds. Unlike the original characterization, these explicitly assert
C09 PermissionError with prior bytes preserved and C08 successful replacement.
After-fix JSON filenames are distinct, preserving the original failed-boundary
evidence. RP-SI04 is closed; this does not close RP-SI05.

## RP-SI05 independent fix verification

For a mismatched existing sidecar, `_CacheBuild.publish` now captures the sidecar's
own mode, requires a nontruncating write-open and applies that mode to its staged
version file before writing/replacement. Matching version-1 sidecars remain
untouched. The check precedes accepted Parquet publication; denial therefore
preserves both prior data and the old sidecar, improving the old failure order
without bypassing its authorization boundary.

`reports_sidecar_authorization_after_probe.py/.log`: **6 current cases passed**,
9.25 seconds. Two real 0444 cases assert PermissionError and unchanged data plus
sidecar bytes/mode. Four successful repairs verify each consumer preserves its
sidecar's own 0600 or 0640 mode when its Parquet mode differs. Original sidecar
characterization JSON/logs remain separate. RP-SI05 is closed.

The parent's `reports_readonly_sidecar_tests.log` independently records **93
passed**, including normal report/archive workflows and the new target/sidecar
regressions. Earlier 89-test target-only and original 87-test results remain
retained. Reviewed `_cache_freshness.py` SHA-256 after both corrections:
`2f999913fc0557f7ea68a08f0c8bef7b3048a062dd9665afb5a9ddceed73ff24`.

## Disposition and limits

The preceding report security review's scoped PASS was reopened for these
follow-up findings and is now restored after independent fix verification.
Neither finding needed a new permission policy or risk acceptance: both fixes
restore the existing access contract. C08's proven native data-file replacement
behavior remains unchanged. No unresolved medium/high finding remains in this
bounded report review.

This probe covers mode 0444 under UID 1000 on the local container filesystem.
It does not characterize named projects, ACL matrices, cross-filesystem links,
all worker/browser identities or read-only mounts. Runtime
acceptance remains separate. Original artifacts are retained for comparison.
