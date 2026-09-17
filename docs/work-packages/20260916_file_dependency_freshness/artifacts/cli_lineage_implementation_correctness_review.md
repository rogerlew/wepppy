# PF-R02 implementation correctness review

Independent reviewer: `freshness_correctness`, 2026-09-17. Scope: implementation
after checkpoint `166c8f79d`, including the subsequent attempt-directory descriptor
correction. No production/test edits. **Scoped code/probe PASS: no additional major
correctness defect identified. Final affected/performance/runtime gates below
remain separate from this disposition.** This does not close the work package.

## Generation and selection binding

`wepppy/climates/cli_parquet.py:_CliParquetAttempt` copies bounded bytes from one
opened regular source descriptor, hashes those bytes while copying, checks its
descriptor/path version and verifies the live source digest. Both producers parse
only the retained `source.cli`. The native/dataframe calculation blocks remain
the existing operations under the attempt context, with additive Arrow metadata
and `preserve_index=False` matching the original export contract.

The candidate's proof describes the snapshot selection/digest, not a later source
read. Before replacement, the Climate producer calls the canonical owner reload
and the interchange producer reapplies its hint/fallback selector. Final source
content is checked uncached. The normal detached-owner selection regression is
meaningful; it does not merely mutate the exporter object's own field. Existing
NoDb cache semantics remain the owner authority; this review does not certify an
unrelated arbitrary same-stat mutation of `climate.nodb`.

Actual change-and-restore during snapshot parsing leaves rows and proof tied to
the stable snapshot. A lasting rewrite or changed selected path rejects the
candidate. Empty/header parser exceptions retain propagation and failed-attempt
evidence; the existing caught exporter errors retain logged-None behavior.

## Publication and retained work

Publication writes Arrow through an opened exclusive candidate handle, retaining
partial backend output on failure. Existing canonical bytes remain untouched
until atomic replacement. Source snapshots are protected by an attempt directory
that is private from creation. The corrected implementation traverses the new
artifact subtree through directory descriptors with no-follow checks, writes
payloads/status relative to its retained descriptor, and checks the directory's
identity before publication. Security's separate escape probes own that finding.

The final code writes ready status before owner/source/destination rechecks, then
publishes from the pinned attempt directory. It preserves the existing target
symlink and access mode and verifies inode write authorization without truncation.
A successful replacement immediately sets `committed`; diagnostic and expected
notification failures cannot undo it or report an uncommitted export. Attempt
status remains useful when a postcommit write fails.

The new skeleton allowlist entry retains the entire `climate_artifacts` module.
The added actual cleanup/skeleton/archive regression checks failed snapshot/status
bytes before and after normal working-directory cleanup, canonical archive member
creation and restore. That is stronger than checking only an allowlist literal;
authorized browser access remains a separate runtime gate.

## Readiness and legacy behavior

`production._cli_lineage_current` uses the caller-owned source selection under
existing post-fire containment/no-follow rules. Receipt paths are comparison data,
not authority to open another file. `_read_proof` validates framing/footer size,
then exact proof fields, duplicate keys, types, digest and accepted producer/
interpretation versions. Unsupported/absent/malformed proof cannot certify a new
execution. Required read failures do not become a legacy success.

The footer observation is bound to its descriptor version and compared with the
path/inventory observation. The active source digest is checked even when
`content=False` disables the full hash map. `_current_authority` consumes the
resulting climate check, so the locked authority path does not silently omit this
new prerequisite. No lineage fields were added to accepted-result snapshot
equality: existing historical source/artifact validation remains independent.
Interchange's existing-file fast path still reads legacy tables without creating
proof. Currentness is not revoked merely by a failed redundant export with an
otherwise matching prior proof.

## Retained direct evidence

`cli_lineage_implementation_correctness_probe.py/.log` records **5 passed** using
actual owner fixtures, ClimateFile, Arrow output and source checks:

- Replace the canonical Parquet after reading its proof: both full-content and
  `content=False` source checks raise `changed_source` rather than associating the
  opened proof with the replacement generation.
- Fail the complete-status write after commit: exporter returns its output,
  precipitation is 8 mm, readiness is true, and ready-to-publish evidence remains.
- Force two producer attempts to overlap at the publication boundary: both
  return complete output and retain distinct complete attempts; accepted rows and
  source proof agree.
- Remove an interchange hint while parsing its snapshot: the new fallback
  selection causes candidate rejection, without publishing obsolete hinted rows.

Reviewed `cli_lineage_focused_revision3.log`: **84 passed** across the then-current
affected suite. The initial failed timestamp-only expectation was appropriately
changed to actual changed bytes under the ratified metadata-only contract; its
failed log remains. Later test additions cover uncaught parser exceptions,
footer size limits, opened-old generation, competing distinct-source publications,
artifact retention, initial subtree escape and postcommit status failure; their
final combined run must be retained before completion.

## Remaining gates

Repeat final affected tests and implemented performance, rather than substituting
the preimplementation composition. Exercise the 5-ms settled/40-ms cold-evicted
lineage budget with actual eviction and zero settled CLI payload rereads, and the
1.5-second/200-ms-added 120-year export budgets including owner/status checks.
Retain exact rows/types/calendar propagation and breakpoint coverage through the
actual producers and downstream interchange/model artifacts.

Normal owner reload and whole-project state costs remain outside the lineage
component measurement. Cross-filesystem destinations, managed NoDir layouts,
real browse/download identities and final deployment acceptance are not proved
by these disposable probes. No claim of arbitrary concurrent-writer isolation or
full package closure is made. Any remaining independent security finding must
also be resolved before handoff.
