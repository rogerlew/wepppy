# WEPP run input contract

## kslast omission

Accepted and Forest conformance validated 2026-09-19; production rollout is
separate. This bounded contract
covers the shared WEPP parser used by JSON/form run submissions and direct
`Wepp.parse_inputs` callers. Other fields retain their current contracts.

An absent `kslast` key must preserve the saved conductivity override, including
zero, None, or a legacy absent attribute (whose property reads None). Omission
must not synthesize a new value. Explicit null, empty string, or existing
case-insensitive none-prefixed strings clear the override. Existing numeric
conversion and list/tuple/set first-nonempty selection remain unchanged;
explicit empty collections retain their clearing behavior. Other unrecognized
values retain the existing parser behavior, not a new validation policy.

Rationale: partial API submissions must not silently change an unrelated soil
parameter. Clients clearing this parameter must submit it explicitly. Initial
saturation, compiler selection, pass families, units and defaults are unchanged.
The existing NoDb lock/persistence and rq-response contracts still apply.

Evidence must exercise the real parser through its locked facade, reload durable
state and read prepared soil files. Retained artifacts use existing `wepp.nodb`,
`soils/hill_*.mofe.sol`, `wepp/runs/p*.sol`, logs and output paths, normal project
browse/download and canonical archive/restore. Failure is not completion; no
new status mechanism or error translation is introduced.

## Single User-Defined Builder exception (2026-09-25)

SUDI-01, [Single User-Defined inputs](single-user-defined-inputs-contract.md), defines the bounded creation-time exception to ordinary
Builder Disturbed support and adds independent mode5 landuse/soil uploads.
Checked projects exclude Disturbed/SBS and their dependent features across UI,
activation and direct execution, and disable buffer geometry and management
overrides. Unchecked/legacy behavior remains unchanged. The checkbox does not
select an input mode. Preserve the option through capability refresh and preserve
accepted sources across rebuilds/mode switches. Compatible cover/soil modifiers
retain their existing precedence on generated copies; all non-buffer OFEs receive
the selected single source on a mode5 build. Subsequent explicit class edits
and global mappings retain existing modification contracts and may replace
assignments; rebuilding mode5 restores uniform source assignments. These edits
do not initialize Disturbed or apply its lookup transforms. Existing authorization, response, persistence and
controller invariants remain in force. This explicit exception governs where
earlier unconditional Disturbed statements conflict; no other defaults change.
Implementation conformance is pending the SUDI-01 checkpoint and validation.

## Continuous watershed runtime budget (WRT-01)

Operator approved 2026-09-28; implementation pending. Continuous watershed child
jobs use `3600 * max(12, ceil(years * hillslopes / 72000))` seconds: equivalently
0.05 seconds per hillslope-year, rounded up to whole hours with a12-hour floor.
Preserve a larger explicitly supplied pipeline timeout rather than reduce it.
This is an execution allowance, not a scientific parameter or runtime guarantee.
The empirical rationale is in [the wepp1 assessment](../investigations/20260928_wepp1_watershed_timeout_scaling/assessment.md).

Apply identically to full, full no-preparation, watershed-only, and watershed-only
no-preparation pipelines. For preparation paths use positive integral
`climate.input_years` and `wepp.watershed_instance.sub_n`. For no-preparation
paths, the owned continuous `wepp/runs/pw0.run` is authoritative: use its
hillslope-count record and final simulation-years record, without rewriting it
or requiring current saved settings to match. Both legacy master-pass prompt
and modern omitted-prompt layouts are supported. Read at most1MiB. Missing,
malformed, nonpositive or nonintegral workload inputs fail explicitly before
enqueueing any children; never silently substitute a default workload. Existing
valid integer-string year representations are accepted.

Single-storm modes (including batch) retain their existing timeout and do not
require continuous workload fields. Hillslope-only/preparation-only pipelines
do not read unused watershed-budget inputs. Other stage timeouts and dependency
edges remain unchanged. Compute and validate the budget before the first enqueue
in each applicable pipeline to avoid partial graphs on workload errors.

Store additive child job metadata under `watershed_timeout`: policy `WRT-01`,
`years`, `hillslopes`, `seconds_per_hillslope_year` (0.05), `timeout_seconds`,
`workload_source` (`controllers` or `prepared_run_file`) and selected `wepp_bin`.
Preserve fork-failure lineage and other existing metadata. No NoDb schema changes.
Absent optional fork metadata is normal. No new UI fields or caller-supplied
timeout overrides are introduced. This finite calculated budget has no new
arbitrary cap; it must fit the positive platform/RQ alarm range (2^31-1 seconds).
Reject an out-of-range computed/supplied budget explicitly, never silently clamp.

Existing RQ errors, auth, locks, output and completion semantics stay unchanged.
Failed jobs keep their previously stored timeout; only new submissions receive
the policy. Deployment, retrying production jobs and subprocess cleanup changes
are outside WRT-01. Validate actual serialized RQ job timeout/metadata and the
unchanged dependency tree on a disposable development run, including no-prep
source immutability.
