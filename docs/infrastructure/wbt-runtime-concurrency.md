# WBT runtime concurrency

Default and batch worker services in the dev, dev.hpc, prod, and prod.worker
Compose configurations set `WBT_MAX_PROCS: ${WBT_MAX_PROCS:-12}`. Host overrides
such as wepp1 inherit these environment keys. Set a positive integer in the
Compose interpolation environment to override 12.

The WBT runtime precedence is environment WBT_MAX_PROCS, then settings.json
max_procs, then -1 (automatic selection). An absent standalone environment variable
preserves legacy behavior. An unset or empty Compose interpolation variable instead
selects the Compose default 12. Empty, non-integer, zero, or negative values passed
directly to WBT are rejected. Available CPUs can limit the effective thread count
below the configured budget.

No NoDb field or UI control is involved. The existing Python wrapper inherits the
worker environment into each subprocess; concurrency configuration does not write
settings.json. The legacy setter and CLI --max_procs remain persistent operations
and should not be used for per-job changes. If both are supplied, the environment
wins during execution while the explicit CLI setting retains its persistent value.

A WBT build supporting this variable must accompany this configuration. Older
binaries ignore it. Validate the rebuilt CLI and existing container wrapper before
rollout; this change does not itself deploy or alter queue concurrency. See
[ADR-0051](../adrs/ADR-0051-wbt-runtime-concurrency.md) for provenance and rationale.
