# CLI-to-Parquet lineage discovery

Independent security/noninterference discovery by `freshness_security`,
2026-09-17 UTC, after `0f2826a25`. No production/test edits or named-project
mutations. This supplies contract design inputs; it is not implementation approval.

## Findings first

| ID | Severity / disposition | Actual boundary and required correction |
| --- | --- | --- |
| PF-R02 | Medium, OPEN | Existing readiness admits a different active CLI than the exported rainfall. In addition to the retained equal-size/restored-time case, a rewrite or actual selected-filename change after parsing produces Parquet precipitation 4 mm, current CLI precipitation 8 mm and readiness true. Bind successful output to the exact selected source bytes parsed, then verify that association at admission. |
| PF-CLI01 | Medium, OPEN | A controlled ENOSPC at the real PyArrow writer boundary truncates the previous canonical Parquet to four bytes; PyArrow error cleanup then removes it. Parse and read failures earlier in export preserve the old file. Publish a separately allocated completed candidate; never pass the prior accepted path to a destructive writer. |

These are data-integrity/working-behavior findings, not demonstrated auth bypasses.
The source-race probes inject a normal rewrite/selection change after actual
parsing; they do not claim arbitrary concurrent-writer isolation. Accepted-result
hashes already detect changed CLI bytes, but that does not prevent a new attempt
from consuming an independently stale Parquet. PF-R02 remains a package blocker.

## Evidence retained

Run through the actual Docker environment:

```text
wctl run-pytest docs/work-packages/20260916_file_dependency_freshness/artifacts/cli_lineage_discovery_probe_revision2.py -v -s --maxfail=1
wctl run-pytest docs/work-packages/20260916_file_dependency_freshness/artifacts/cli_lineage_candidate_probe.py -v -s --maxfail=1
```

The corresponding logs record **10 passed** and **2 passed**. Assertions
characterize existing defects and demonstrate bounded candidate feasibility;
they are not acceptance tests for an implemented repair.

- The real ClimateFile parser, peak-intensity implementation, pandas/PyArrow
  writer, real NoDb Climate selection and `production.sources` are used. Source
  rewrite and `cli_fn` changes both expose the 4-versus-8 mm mismatch without
  timestamp restoration. The original `postfire_remaining_probe.py/.log`
  separately retains the touch/restored-time defect.
- Real UID 1000 read denial and malformed numeric CLI parsing return None and
  retain prior Parquet bytes. They do not become successful exports.
- `ParquetWriter.write_table` alone is replaced by an explicit ENOSPC seam;
  the real native constructor opens/truncates the path and real PyArrow cleanup
  removes it. `cli_lineage_pyarrow_writer.txt` retains installed implementation
  evidence: path-like destinations are removed on exceptions. The original
  `cli_lineage_discovery_probe.py/.log` expected damaged retained bytes and
  failed with FileNotFoundError. Revision 2 asserts the actual deletion; the
  failed original is retained rather than rewritten.
- Existing exporter follows an input symlink outside `cli_dir` (still inside
  the disposable run) and preserves an output symlink plus its target mode 0640.
  This is exporter behavior, not permission for post-fire consumers to bypass
  their stricter nonsymlink project containment.
- `_ensure_cli_parquet` actually exports 4 mm from the first sorted CLI without
  a hint, or 8 mm from the hinted CLI. Both outputs carry only `pandas` and
  `ARROW:schema` metadata: no producer receipt.
- A failed separately allocated candidate written through an opened file handle
  remains on disk (11,197 bytes) and leaves the previous canonical bytes intact.
  Passing the handle avoids PyArrow's path-unlink cleanup. An opened ParquetFile
  also returns matching old rows and old embedded metadata after pathname atomic
  replacement, while a new opener reads matching new rows and metadata.
- A 154,409-byte repository CLI with 2,192 rows exports through the actual service
  in 63.17 ms. Copy plus three SHA reads takes 2.41 ms; a separate metadata rewrite
  takes 5.09 ms. Output is 151,247 bytes. These are one local warm-storage sample,
  not a large-run budget or justification for an extra full serialization pass.
  Adding a private metadata key preserves exact pandas rows/dtypes and survives
  an ordinary file copy. The source fixture's digest remains unchanged.

## Existing owners and contracts

`ClimateArtifactExportService.export_cli_parquet` reads `climate.cli_fn` once,
constructs `Path(climate.cli_dir) / cli_fn`, parses it, computes existing calendar
and intensity columns, then writes `wd/climate/wepp_cli.parquet` directly.
`ClimateFile.__init__` opens the selected file once and stores all text lines;
`as_dataframe` consumes those lines. It currently accepts a path, not an input
file handle. Peak-intensity calculations use the existing owned native climate
helpers; there is no native CLI-to-Parquet publication API to amend.

The export exception boundary catches listed parse/backend/read/write failures,
logs with source context and returns None. Missing selection/file returns None.
`export_post_build_artifacts` sleeps one second, exports frequency data only on a
non-None Parquet result, then handles Atlas14. Sleep is not a publication or
lineage guarantee. Both `ClimateBuildRouter.build` and `set_user_defined_cli`
can timestamp climate completion after this optional export fails.

The production M1 contract, `docs/production_m1.md` under "Publication verification
and reuse," explicitly requires Parquet no older than the active CLI to reject
old event data after export failure. Current implementation conforms to that
requirement. A producer-proof replacement needs an ancestor contract amendment,
including the shared file-dependency contract; deleting the mtime clause alone
does not fix the proven behavior. M1 and M3 use this shared readiness path.

`production.sources` also enforces Climate completion after abstraction and
tracks selected filename, climate options, active CLI and Parquet separately.
`_current_authority` calls it with `content=False` during finalization; the new
association cannot simply disappear from that path. Keep strict transaction
versions/owner ordering separate from accepted-content equality. Rainfall uses
the Parquet under existing no-follow, size, row, column and hash checks.

The second producer is `wepppy/wepp/interchange/_utils.py::_ensure_cli_parquet`.
It returns any existing
canonical Parquet without rebuilding; otherwise it selects an explicit hint or
the first sorted CLI and duplicates export transformations. Its calendar callers
do not establish authoritative Climate selection. It may record its actual source
if included in the new wave, but must not claim it selected today's Climate CLI.
Do not add a new polling-time call to this materializer.

The RUSLE specification's "Hyetograph API and Breakpoint Artifact Compatibility"
section requires current canonical/legacy intensity columns, nullable breakpoint
`tp`/`ip`, correct duration and zero-rain semantics. Private footer metadata can
be additive; do not change dataframe schema, equations or calendar ordering.
Skeletonization explicitly retains `climate/*` and canonical Parquet. Embedded
evidence naturally travels with the file; an additional required sidecar needs
its own archive/skeleton retention and two-file commit design.

## Smallest compatible design to ratify

1. **Producer-owned, same-file evidence.** Embed a bounded, versioned private
   metadata object in the completed Parquet: actual selected run-relative source
   identity, source SHA-256 and explicit exporter interpretation revision. Preserve
   pandas/Arrow metadata. Bind rows and evidence in the same candidate and publish
   them together. Readiness derives allowed paths from the existing owner and
   compares the recorded identity; a receipt must never direct a filesystem read.
   Absolute runtime paths are diagnostics, not portable archive identity.
2. **Bind the bytes actually parsed.** Capture selection and resolved source
   observation, preserve a unique visible source copy while hashing its bounded
   captured bytes, then parse that copy with unchanged ClimateFile. Verify live
   source content/selection again before publication. A separate hash of today's
   CLI after parsing cannot certify the previously parsed rows. Reuse existing
   descriptor/path coherence rules; do not invent an arbitrary-writer isolation
   claim. An alternative that reads/hash-parses one descriptor needs demonstrated
   parser compatibility before replacing this bounded retained-copy approach.
3. **Atomic output and retained failures.** Create an exclusive visible attempt
   on the destination filesystem. Write directly from the final dataframe to
   an Arrow table with added metadata once, through an opened candidate handle,
   preserving failed source/candidate/diagnostics. Recheck selection/destination
   and existing mode before atomic replacement. Prior output and its proof remain
   untouched until commit. After commit, notification/diagnostic failure must not
   claim the replacement never happened or attempt an unsafe rollback.
4. **Read a coherent association.** Validate bounded footer structure/version,
   source identity and digest against the owner-selected current CLI. Tie the
   proof observation to the exact Parquet generation admitted/hashed, not a later
   pathname stat or independently reopened footer. The existing accepted-result
   full Parquet hash continues to bind exact output bytes. An embedded source
   claim is not an output checksum or adversarial authenticity signature; the
   design trusts the owned producer and detects changed source generations.
   If the threat model requires detecting arbitrary row edits that deliberately
   retain forged metadata, this evidence alone is insufficient and that stronger
   scope must be explicitly specified rather than implied.
5. **Bounded local readiness.** State reads perform no export, copy, receipt
   migration, network access or owner mutation. Missing source, malformed proof,
   access failure and content mismatch remain distinct observations; none silently
   authorizes fallback to timestamp proof. Preserve existing post-fire no-follow
   checks, receipt order, downstream source hashes, snapshots and finalizer guards.
   Footer/cached-source checks need their own measured cold, unsettled and settled
   budgets including `content=False` callers. Do not globally narrow general
   Climate source formats/symlink behavior to the post-fire consumer's rules.

## Compatibility decisions still required

- **Proofless legacy:** present-day hashes cannot fabricate past producer
  lineage. To close PF-R02 for new executions, these files cannot be labeled
  verified merely because mtime passes. The smallest strict policy is an explicit
  existing owner rebuild/export action before a new model run, retaining old
  reports/downloads under their existing accepted hashes. This changes readiness
  for otherwise usable legacy runs and requires explicit contract acceptance.
  Keeping a documented legacy mtime branch instead preserves old admission but
  retains the demonstrated defect in that branch; do not call PF-R02 fully closed.
  Read-only recomputation/parity is a separate measured migration proposal, not
  permission to build silently during state reads.
- **Second producer:** include `_ensure_cli_parquet` with actual selected-source
  evidence, or explicitly classify its proofless output under the legacy policy.
  Adding proof to only the Climate owner does not eliminate this supported
  proofless producer. Existing malformed/new-format proof must not downgrade to
  legacy, and exporter revision incompatibility needs an explicit disposition.
- **Historical/archive behavior:** retain accepted result/download validation
  and raw Parquet report readers. Missing CLI prevents claiming new verified
  readiness; it must not delete an already accepted result or fabricate source
  hashes. Adding a new selection field can stale every old accepted snapshot;
  define versioned comparison before changing that schema. A full relocated
  archive must compare portable selected identity, not its former absolute root.
- **Destination topology/access:** direct export currently follows destination
  links and preserves 0640. Atomic replacement of the lexical link would instead
  destroy it. Resolve and recheck the selected target, stage on its filesystem,
  preserve link/mode and ensure candidate visibility never broadens access.
  Managed NoDir roots and existing root-lock orchestration must still work.
  External targets, EXDEV, hard-link behavior and other production identities
  have not been accepted by the local probe. Do not assume report-cache staging
  policy automatically governs climate artifacts.
- **Extent of rollback guarantee:** ordinary ClimateBuildRouter may clear the
  climate directory before export. The repair can preserve a prior artifact
  present at exporter entry; it cannot promise whole-climate-build rollback.
  Producer overlap must follow existing owner/root-lock semantics. Two competing
  candidates cannot be made one transaction by before/after hashes alone.
- **Resource/retention budget:** retained source copies add storage proportional
  to selected CLI size; the reader already loads full text/dataframes. Measure
  supported long records, breakpoint files, NoDir projection writes, source
  copy/growth errors, same-filesystem replacement and browser/archive retention
  before shipping. The small local timing is feasibility evidence only.

Reviewed source SHA-256 values:

```text
climate_artifact_export_service.py 436e26344956d233794f976717e7cf032db097376ff00f266425bb43893cda34
production.py c1ab5c648e076ed301e194f133eb51403f633888c0306f409ca33aeeb8058aae
interchange/_utils.py 7cd34191f538e52a2196f0ca5548375a66b95a2269723bd062fc2f9eb66f3eeb
```

Disposition: discovery complete; PF-R02 and PF-CLI01 remain OPEN pending a
reviewed producer/publication/legacy checkpoint and implementation evidence.
