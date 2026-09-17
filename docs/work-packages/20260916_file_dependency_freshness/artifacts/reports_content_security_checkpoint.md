# C08/C09 report provenance security checkpoint

Independent reviewer: `freshness_security`, 2026-09-17 UTC. Reviewed the proposed
report-cache contract, output-scope amendment, decision artifact, actual report,
query-engine and native implementations, and retained correctness baselines.
No production or test files were edited. Independent probes used disposable
projects under UID 1000/GID 993 through `wctl exec weppcloud`.

## Findings and disposition

**Scoped PASS for the revised preimplementation checkpoint.** The C09
destination precision and measured budgets are now in the canonical contract.
The embedded-provenance design is sound for these bounded consumers, subject to
the preserved boundaries below. This is not a finding that unimplemented code
is already correct and is not runtime/package approval.

- **RP-S01, Medium, resolved in contract:** moving C08 native output into an
  attempt bypasses native validation of the final canonical destination. The
  actual producer rejects symlink/directory output and canonical input/output
  aliasing. The revised publication contract retains these destination checks
  before work and publication. Independent native invocation confirms an output
  symlink raises `OSError` without changing the link or its target.
- **RP-S02, Medium, resolved in contract:** protecting only the final cache mode
  can expose the same restricted report through newly created attempt payloads.
  The actual native producer preserves an existing 0640 destination, but a new
  candidate under umask 0022 is 0644 with identical report rows. The revision
  requires applicable modes from payload creation and restricted attempt-directory
  visibility for native internal staging, without changing process umask or
  runtime identity. Verify actual 0600/0640 behavior in implementation.
- **RP-S03, Medium, resolved in contract:** C09 consumes catalog identifier
  aliases in addition to selected paths and bytes. With uppercase-ID Parquets,
  setting the optional loss catalog schema to `None` preserves all three hashes
  and paths but changes actual query success into `BinderException` for missing
  `wepp_id`; the existing cache still returns rows. Binding effective alias
  expressions prevents a new verified cache from concealing that query change.
- **RP-S04, Medium, resolved in contract:** native symlink rejection is a
  C08 boundary, not the existing C09 behavior. Actual C09 cached reads and a
  schema-triggered DuckDB rebuild follow a cache-file symlink, update its target
  and preserve the link. The revised C09 atomic publication retains this
  selection rather than replacing the link or introducing a blanket prohibition.
  It resolves the target, preserves its applicable mode, rechecks the lexical
  selection before publication and replaces that same target. The disposable
  probe covers a target inside the project on the same filesystem. No repository
  writer creating cross-filesystem report-cache links was found; that case is
  currently an acceptance risk, not evidence authorizing a new staging topology.
  Do not claim untested cross-filesystem support or silently narrow an established
  workflow if such a case is found.

Original and revised probes/logs are retained as
`reports_checkpoint_security_probe.py/.log`, `_revision2.py/.log` and
`_revision3.py/.log`. All three commands exited 0. They exercise actual native
aggregation, ReportQueryContext/catalog loading and DuckDB report queries;
reported rows and native results are not mocked. Revision2 adds the mode
characterization; revision3 adds the C09 symlink read/rebuild characterization.

## Consumed identity and coherent publication

`HillslopeWatbalReport._build_summary` consumes native-discovered WEPP IDs and
the effective `Watershed.translator_factory` mapping, with in-memory summaries
before hill/channel Parquet fallback. Roads optional-manifest targets and raw-ID
fallback are part of the effective mapping; unrelated manifest attributes are
not. Empty native ID sets correctly avoid a translator dependency. Retained IDs
can safely avoid a repeated large-source scan only when source bytes and valid
embedded provenance agree.

`AverageAnnualsByLanduseReport._build_dataframe` consumes loss, hillslope and
landuse tables through the actual catalog. `build_query_plan` uses `catalog.root`
and `_resolve_dataset_path`, not simply the report working directory. Preserve
that resolver, permitted parent-run assets and effective aliases. Compare a fresh
selection after work; a second context that selects different files cannot verify
the context that produced the rows. Portable run-relative identities and parent
relationships are appropriate for archive relocation; actual resolved paths stay
diagnostic observations and never authorize a new read.

Rows and versioned provenance read from one opened Parquet avoid a separate
mutable source-to-cache sidecar association. Validate the embedded schema and
required fields: unknown or malformed proof must not become a legacy fallback.
The version-only sidecar remains compatible with older readers. Compact Arrow
rewrites must preserve types, field order and pandas metadata, including empty
native outputs; no full H.wat pandas conversion or scientific formula change is
authorized.

Unique visible attempts avoid shared partial output names. Dependencies are
captured before work and checked after work; a final hash alone cannot prove
earlier rows. Atomic complete-Parquet replacement is the stated commit point.
Required sidecar/status work precedes it, and a later diagnostic failure must not
roll back another publisher or misreport an already committed generation as a
failed build. Concurrent last-complete-writer publication is acceptable when
each file contains its own rows and provenance. This is bounded observation,
not arbitrary-writer transaction isolation.

## Historical, access and error states

Historical access preserves the demonstrated cache-only reports. It is not a
successful freshness check. Require actual missing selected prerequisites;
inspect still-available dependencies even if another is absent. A changed
available dependency, denied read, malformed required table or incoherent read
cannot be hidden by an early absence return. Translator `RuntimeError`/`KeyError`
must not be broadly reclassified as missing archival resources. Preserve its
actual selection precedence and distinguish empty from absent inputs.

For legacy C08 with unavailable native API, preserve only the old source-newer
rule's explicitly unverified availability. The existing
`WeppInterchangeUnavailableError` distinguishes unavailable API from execution
failure; a native parser/I/O exception is not a compatibility escape. Rebuild
legacy rows when prerequisites are available, never stamp them with today's
source hashes. A known verified mismatch must not fall through to an older
baseline cache. Additive `cache_status` and historical logs communicate the
distinction without changing scientific CSV columns or claiming an HTML badge.

Required hashes retain read checks on settled reuse. Optional Roads manifest
read/parse failure already logs and falls back; preserve that optional policy
instead of applying required-source rejection to it. Scope, authentication,
normal URLs, join formulas and permission boundaries remain unchanged. Restrict
new helper behavior to these two keys rather than silently changing every
`ReportCacheManager` consumer.

## Acceptance still required

The contract correctly keeps accepted caches and failed/partial attempt work in
ordinary project paths. Canonical `project_rq_archive` includes these paths;
this source inspection does not replace actual archive/restore, browse and
download evidence. Verify restored bytes and portable freshness after moving a
disposable run, both successful and failed attempts, and actual service identity,
groups, mounts and umask. Native failure before a compact output exists must
still leave visible attempt observations/error status; do not claim a summary
was retained when the producer never returned one.

Reviewed performance revision3 distinguishes helper-cache cold from physical
storage cold: 81,150,978-byte H.wat hashing takes about 0.273 seconds, settled
checks 0.224 ms with zero hash bytes; ID scan 0.139 seconds, native summary
0.937 seconds, and retained-ID observation with disk hydration 4.10 ms. C09
context/alias selection takes 2.54 ms, settled observation 4.08 ms and the actual
DuckDB query 33.0 ms. These are component baselines, not acceptance of the new
full report constructor. The final contract budgets additional settled C08
validation at 10 ms for persisted summaries or 30 ms for Parquet translation,
and C09 at 10 ms. Representative initial/changed builds, including annotation
and publication, must fit 2 seconds for C08 and 100 ms for C09, with at most two
hashes per selected source. These bounded budgets are consistent with the retained
baseline and are not runtime timeouts. Implementation must demonstrate actual
cold/admission/eviction and settled costs, including real controller acquisition.
Real mutation, concurrent opened-file replacement, publication failure,
malformed proof, partial archival absence, permission denial, selected parent
assets and scope isolation remain implementation/runtime gates.
