# CLI lineage implementation security review

Independent reviewer: `freshness_security`, 2026-09-17 UTC. Scope: implementation
after checkpoint `166c8f79d`: `wepppy/climates/cli_parquet.py`, both producers,
post-fire readiness and skeleton retention. Only disposable probes and artifacts
were written by this reviewer. No named-project mutations.

Final scoped security disposition: **PASS after the verified corrections below**.
No unresolved medium/high security finding remains in this bounded implementation.
This does not approve the affected-suite/performance gates or deployed runtime.

## Findings and current disposition

| ID | Severity | Disposition / evidence |
| --- | --- | --- |
| CLI-I01 | Medium | CLOSED after independent correction verification: every newly introduced artifact-directory component could follow a symlink outside the run. Actual interchange export succeeded and wrote its raw snapshot outside the project for all three components. Anchored no-follow directory creation and held-descriptor payload writes now reject these cases without outside writes. |
| CLI-I02 | Medium | CLOSED after independent correction verification: exporting through a supported alias of the project root produced a nonportable source identity and made the canonical post-fire owner unready for unchanged data. Logical selection is now relative to the corresponding logical project root, with separate resolved identity; actual alias export now passes canonical readiness. |
| CLI-I03 | Medium | CLOSED after code correction and archive verification: initial raw snapshot/status modes depended on directory-only privacy, but archive restore preserves file modes while recreating directories with default permissions. They now use 0600 from creation and remain 0600 after actual restore. The fix landed before the original characterization imported the helper; no pre-fix exposure reproduction is claimed. |

The contract review's PASS does not substitute for this implementation review
or the separate runtime/performance gates.

## Retained direct evidence

`cli_lineage_implementation_security_probe.py/.log`: **8 passed**, 19.56 seconds.
Three assertions characterize the original artifact-root defect; the other five
exercise actual generation, bounds and access checks. These were not all repaired
acceptance assertions.

`cli_lineage_implementation_security_after_probe.py/.log`: **8 passed**, 21.18
seconds, after the directory-descriptor correction. Tests use real ClimateFile,
interchange production, Arrow metadata and actual post-fire owner fixtures.

- Symlinks at `climate_artifacts`, `cli_parquet` and `attempts` initially produce
  one source snapshot each in a sibling directory outside the disposable run.
  The private leaf remains 0700: confidentiality bits alone did not establish
  path authority. The after probe requires export failure, zero outside snapshots
  and an entirely unchanged outside directory.
- Replacing canonical Parquet after its real proof read raises `changed_source`
  under both `content=True` and `content=False`; proof from one descriptor is not
  accepted for a later observable path generation.
- A real file with a footer above the byte limit is rejected before decoding. The Arrow
  constructor seam would raise if called; the actual framing/size check raises
  ValueError first.
- Real UID 1000 read denial on the active CLI and on the Parquet raises
  PermissionError in the locked-authority path; denial does not become readiness
  or a proofless-legacy fallback.

`cli_lineage_root_alias_probe.py/.log`: **1 characterization passed**, 16.95
seconds. The actual interchange producer is invoked through a sibling symlink
alias of the same fixture run. It initially records
`../<run>-alias/climate/owner.cli`, though resolved identity is `climate/owner.cli`.
Actual `production.sources` through the canonical root then reports unready.
`cli_lineage_root_alias_after_probe.py/.log`: **1 passed**, 16.87 seconds; both
identities are now `climate/owner.cli` and canonical readiness is true. Source
and output link capabilities were preserved, not forbidden to hide the defect.

The original files/logs remain separate from after-fix assertions. These are
disposable local integrity probes, not an arbitrary-writer isolation proof.

`cli_lineage_archive_permissions_probe.py/.log` retains a **failed characterization**:
the helper's 0600 correction landed before import, so its expected old 0644
snapshot assertion did not hold. Actual output records directory 0700 to 0755
across restore and snapshot 0600 to 0600. Do not describe this as a runtime
reproduction of pre-fix snapshot exposure. The initial implementation's default
0666 payload creation and the actual restore behavior establish the code concern;
the revised independent assertion verifies the correction.

`cli_lineage_archive_permissions_after_probe.py/.log`: **1 passed**, 15.08 seconds.
It starts with a real source chmod 0600, uses the existing actual cleanup,
skeletonization, ArchiveRuntime ZIP creation and restore workflow, verifies all
retained bytes, and checks the restored snapshot and every attempt status file
remain 0600 despite recreated 0755 directories. This avoids changing global
archive permissions or relying on private-directory preservation that restore
does not provide. Output candidate modes keep the existing output's policy.

## Reviewed boundaries

The new artifact namespace is anchored at the already accepted resolved run
directory. Each newly owned component is created/opened relative to a held
directory descriptor with `O_DIRECTORY|O_NOFOLLOW`; the unique leaf is private at
creation. Source/status/candidate files use exclusive descriptor-relative opens,
and status plus publication source rename use that descriptor. Before parser
use/publication, the visible attempt path must still resolve to its own expected
location and inode. Existing source/output/wd aliases retain their own accepted
selection semantics; containment is not imposed indiscriminately on old paths.
Raw snapshot and diagnostic files use owner-only modes themselves, so archive
restoration does not broaden their effective readability.

Source acquisition streams no more than the captured size plus one detection
byte, hashes exactly the copied bytes, validates regular descriptor/path identity
and verifies the live source uncached. ClimateFile parses the retained copy.
The candidate embeds its selection/hash, then publication freshly resolves the
owner or interchange selector and rechecks content. A later live hash is not
mistaken for the identity of independently parsed rows. NoDb's existing owner
cache contract remains separate from this wave's source-file integrity claims.

Existing canonical write permission is checked by a nondestructive write-open,
including before final replacement. Output mode and selected symlink target are
preserved; first-create uses umask. Candidate write failures retain partial work
through the opened file handle. Canonical rows and their embedded proof are one
atomic replacement; completion/notification errors after that commit do not
remove the new generation or misreport an uncommitted failure.

Readiness uses existing post-fire `safe` and `open_local` authority and file
bounds. The reader checks framing and footer size before decoding, enforces the
exact supported proof schema/versions and duplicate-key rejection, and compares
recorded paths only to owner-derived observations. It does not open receipt-named
paths. Source content is still checked for `content=False`; full inventory hash
collection and lineage verification are distinct operations. Missing/malformed
proof cannot authorize a new run, while interchange's existing-file calendar
path and independently validated historical results remain compatible.

No scientific columns/formulas, rainfall calendar policy, native intensity
implementation, source-selection precedence, completion ordering or accepted
result snapshot schema changed in the reviewed integration. The retained-copy
and Arrow metadata conversion must continue to satisfy exact-row/type parity.

## Other evidence and remaining limits

The parent's `cli_lineage_focused_revision3.log` records 84 passing affected
tests at that revision; `cli_lineage_new_boundaries.log` adds 17 passing cases
covering parser errors, opening an older generation, overlapping publications,
cleanup/skeleton/canonical archive retention and post-commit status failure.
Correctness independently retains five passing source/proof replacement,
post-commit, overlap and disappearing-hint cases. Final combined test/performance
results must be retained; these intermediate counts are not a final runtime claim.

At final security review, the broader `cli_lineage_affected_tests.log` records
583 passes and one failure in the preexisting M3 runtime fixture; its disposition
belongs to the parent/correctness acceptance gate and is not silently waived.
QA's first implementation-performance artifact also needs explicit budget
disposition; do not substitute prototype or favorable export-only timing for
the settled readiness requirement. These open gates do not change the scoped
security findings' verified closure.

The general exporter preserves supported links while post-fire keeps stricter
no-follow containment. EXDEV/external destinations remain an explicit unproven
compatibility risk, with no new staging fallback approved. Browser/download
access under production identities, NoDir projection layouts, actual full
readiness cost and long-record/breakpoint/downstream propagation remain separate
acceptance work. The first-wave ordinary-digest observation/admission assumptions
remain unchanged; this review does not promise arbitrary concurrent-writer or
filesystem-wide isolation.

Reviewed SHA-256 values after the corrections:

The subsequent same-call directory reuse optimization is independently reviewed
in [cli_lineage_parent_reuse_security_review.md](cli_lineage_parent_reuse_security_review.md),
with nine real filesystem/access probes. The hashes below precede that amendment.

```text
cli_parquet.py ef48004ff552b20ef5206b7b42d7b078dd0a2201003cfaa45ed772c09c5ac74f
climate_artifact_export_service.py 221901b6e643fd6f3cfe89e6e02cdd674ccef86604363a65ceb2977cb8dd5d2a
interchange/_utils.py 94e589a57107c061381d77ef5554aa650abffda32df9be126d7454bad8833ea9
production.py 651b87f0b01dbba6e5e64954bd8df456d87940e8e96a3e61505838f45ccb9481
skeletonize.py 7daef40abb5ed4e061ef6093251e830f2a0ac398fbc4d7a0256174d462fbb95f
```
