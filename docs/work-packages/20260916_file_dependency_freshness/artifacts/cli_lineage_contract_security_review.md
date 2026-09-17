# CLI lineage contract security review

Independent review by `freshness_security`, 2026-09-17 UTC. Scope: the proposed
`docs/schemas/climate-parquet-lineage-contract.md`, the PF-R02 decision artifact,
and production M1 "Publication verification and reuse" amendment. No production
or test edits. The earlier discovery and all failed probe records remain intact.

Final scoped disposition: **PASS after the reviewed amendments below**. No
unresolved medium/high contract-security finding remains. Implementation,
performance and runtime acceptance are separate gates.

## Findings first

| ID | Severity | Disposition / required change |
| --- | --- | --- |
| CLI-S01 | Medium | OPEN in initial draft: new attempts under `climate/wepp_cli.attempts` are deleted by the next normal climate rebuild. Ratify a visible persistent artifact location or explicitly preserve the reserved subtree under every existing cleanup topology. Excluding whole-build rollback does not waive retention of new project records. |
| CLI-S02 | Medium | OPEN in initial draft: preserving output mode bits does not preserve existing target write authorization. Atomic replacement can replace an unwritable existing file when its parent is writable. Require the existing write-access boundary on the selected target as well as directory/publication permission; denial preserves prior bytes and proof. |
| CLI-S03 | Low | Precision requested: bound new footer/JSON parsing, require strict supported proof fields/types, and bind proof to the same Parquet generation admitted in source snapshots, including `content=False` finalizers. Recorded source paths are comparison data, never filesystem authority. |
| CLI-S04 | Low | Precision requested: preserve the existing listed logged-None exception boundary; empty/header-invalid ClimateFile errors can propagate IndexError/AssertionError today. A failed redundant export does not erase the validity of an older successful proof still matching current source bytes. |

Initial disposition: **changes required before checkpoint acceptance** for
CLI-S01/CLI-S02. A follow-up disposition below will record reviewed amendments;
this initial record is retained rather than overwritten.

## Concrete evidence and authority

`ClimateBuildRouter.build` calls `_clear_directory_preserving_symlink_mount`
before ordinary generation. That helper removes the entire regular climate
directory; for managed NoDir projection targets it deletes every child. For an
unmanaged root symlink it drops the link, preserving external contents but losing
their normal project path. Thus simply putting an attempt under the working root
does not satisfy the artifact-observability standard's retained, browsable,
archivable project-record requirement across the next ordinary build.

The proposed alternative `climate_artifacts/cli_parquet/attempts/<uuid>` is an
acceptable bounded layout: an explicitly named Climate artifact module outside
the disposable working directory. The comparable report workflow keeps report
cache/attempt records outside the WEPP output working subtree. Canonical docs
must name the exact inventory, browser and archive paths. Skeletonization's
current `climate/*` allowlist does not cover the new root; its intended retention
must be handled explicitly. This choice avoids modifying general cleanup
behavior, managed projection contents or unmanaged symlink handling.

Current export passes the selected canonical path to pandas/PyArrow's native
writer. The writer needs target write permission. Replacement instead authorizes
the containing-directory operation, so matching final mode bits alone does not
preserve the previous access boundary. Require nondestructive access checking
under the executing identity without inventing a new target-read requirement for
write-only outputs. Existing source/output link selection and effective access
must remain applicable on each attempt; no successful cache observation grants
new access. Candidate/snapshot confinement must apply from creation, not only
after writing sensitive bytes.

The retained discovery log already proves actual source read denial returns None
and retains old bytes, output links preserve a 0640 target, and native write
failure can remove the previous canonical path. Fixing that destructive failure
does not authorize overriding output write denial. Final implementation needs
real identity/mode tests, including writable-parent/unwritable-target failure,
source/output modes and differing worker/browser access where supported.

Readiness currently hashes file content but introduces no Parquet/JSON decoding
at this location. The new decoder should reuse the domain's existing regular-file,
no-follow, byte and Thrift limits rather than expanding a parsing surface during
polling. `rainfall_io.read_table` already specifies bounded Parquet metadata and
forbids external chunks. A metadata-only lineage reader need not decode rows or
create new implicit datasets; it must not follow receipt-supplied paths. Unknown
versions, invalid types/hashes and malformed proof cannot downgrade to legacy.

The phrase "coherent observations" must cover the Parquet generation, not only
matching a CLI digest against a previously read footer. Accepted source hashes,
the embedded proof and admitted file version must refer to the same observation.
Observable changes cause explicit rejection/revalidation. Existing source
rechecks, immutable private snapshots and transaction versions remain necessary;
the metadata is a trusted owned-producer statement, not a signature authenticating
arbitrary writers or a promise of filesystem-wide snapshot isolation.

## Accepted design direction and noninterference

- Both producer entrypoints emit same-file metadata bound to their actual selected
  CLI. The interchange existing-file fast path stays a calendar reader; it does
  not create proof or claim that its fallback selection is authoritative Climate
  state. Preserve explicit hint/first-sorted precedence.
- Parsing a retained verified source copy avoids reopening a changing live file
  and attaching its newer hash to older parsed rows. A fresh content/selection
  recheck precedes publication. Metadata-only source operations remain content
  equivalent; strict read-coherence checks retain their separate role.
- Atomic rows plus embedded proof avoids sidecar commit mismatch. A separate
  candidate preserves the prior output on parse/write/publish failure. Use an
  opened candidate handle where necessary to retain PyArrow failure work; the
  independent candidate probe demonstrates that path-like destinations can be
  deleted by backend error cleanup. Post-commit diagnostic failure cannot undo
  an accepted generation or pretend publication never occurred.
- The explicit legacy decision is coherent: existing proofless report/calendar
  reads and accepted historical result/download contracts remain usable, while
  proofless files cannot authorize a new post-fire execution. Normal owner
  regeneration establishes proof. State polling never builds, stamps or mutates.
  This is an intentional readiness change requiring the proposed ancestor
  checkpoint, not a reinterpretation of old acceptance-time evidence.
- Preserve climate receipt ordering, selected CLI identity and existing source
  and tool hashes. Do not introduce proof fields into old accepted snapshots in
  a way that fabricates historical knowledge or silently changes unrelated
  scientific-currentness semantics. M1 and M3 share the readiness boundary.
- Keep canonical/legacy intensity columns, nullable breakpoint fields, calendar
  indices, existing owned native calculations and dataframe types unchanged.
  The small retained real fixture proves additive metadata feasibility only;
  it does not replace breakpoint, long-record and downstream propagation tests.

## Remaining acceptance limits

Same-filesystem atomic replacement is concrete and appropriate. The draft
correctly leaves externally linked cross-filesystem destinations unresolved;
an EXDEV failure is safe for prior bytes but is not evidence of compatibility
with a workflow that previously wrote directly to that target. Do not ship a
blanket compatibility claim until actual supported topology is characterized.
No new external staging/fallback topology is authorized by this review.

The general exporter supports symlinks while post-fire retains stronger no-follow
containment. Keep the distinction; using the shared ordinary-file digest must
not relax post-fire authority or narrow generic Climate support without a new
decision. New attempt directories must preserve confidentiality and actual
project browser/archive accessibility under production-equivalent identities.

Full readiness/export budgets remain pending, explicitly including cold and
unsettled digest admission, Parquet footer reads and all finalizer callers.
Actual archive/restore, long-record/breakpoint values, NoDir, browser/download
visibility and failed-publication retention remain implementation/runtime gates.
No performance, deployed-runtime or complete-package approval is given here.

## Follow-up disposition: revised canonical contract

Reread the revised canonical contract and decision after the parent incorporated
the findings; the initial findings above remain as review history.

| ID | Revised disposition | Reviewed requirement |
| --- | --- | --- |
| CLI-S01 | CLOSED at contract level | Exact visible `climate_artifacts/cli_parquet/attempts/` layout survives ordinary/managed/unmanaged cleanup; explicit canonical skeleton allowlist and archive/restore retention are required. Earlier climate build cleanup remains unchanged. |
| CLI-S02 | CLOSED at contract level | Existing target authorization requires a nontruncating write-open before publication, in addition to preserved target selection and access bits. Confidentiality applies when attempts are created. Replacement permission alone is insufficient. |
| CLI-S03 | CLOSED at contract level | Exact six-field object, strict integer version, supported producer/interpretation combinations, lowercase SHA-256, comparison-only paths, duplicate/extra-key rejection and framing/footer/proof limits are explicit. Parquet-generation binding and active CLI content validation also apply when `content=False`. |
| CLI-S04 | CLOSED at contract level | Existing caught exceptions retain logged-None behavior, other parser errors propagate with retained evidence, and a failed redundant export does not invalidate still-matching successful proof. |

Correctness independently supplied `cli_lineage_correctness_boundaries.py/.json/.log`:
UID 1000 with writable parent and 0444 canonical output gets logged PermissionError,
None and unchanged prior bytes; empty/header-invalid CLI raises IndexError and
AssertionError respectively with unchanged prior bytes. For this readonly-file
case pandas rejects the path before reaching PyArrow. This refines the native
write-failure evidence without claiming that every export error deletes output.

The revised source check also freshly reloads the Climate owner, while interchange
repeats its own captured hint/fallback selection. That preserves distinct authority
and catches the demonstrated selected-filename race. The exact schema now records
both logical and resolved portable source identity; consumers compare these to
their own observations and never open a receipt-directed path.

The intended proofless-legacy readiness change is explicit in both canonical and
production M1 contracts. It retains old report/calendar reads and independently
validated accepted-result availability. No hidden migration or polling rebuild is
authorized. These revisions resolve the identified contract defects; the actual
implementation must still demonstrate these behaviors, including old state and
denied target preservation, before PF-R02/PF-CLI01 are closed.
