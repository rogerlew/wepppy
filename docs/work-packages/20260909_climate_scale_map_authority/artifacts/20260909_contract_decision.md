# Climate scale-map contract checkpoint

Starting revision: `3c8615387`.

Operator authorization: the 2026-09-09 request says the map should be set from
config and immutable, asks to fix the mutation, and authorizes resetting affected
Portland run configurations. This is an explicit authority change from the
agent API's existing instruction to submit the field.

Canonical amendments: new `docs/schemas/climate-precipitation-scaling-contract.md`
and the Climate Build Ordering section in `docs/schemas/rq-engine-agent-api-contract.md`.
Related unchanged contracts: NoDb persistence/concurrency and RQ responses.

Delta: effective map is config-derived; successful parse persists that value;
legacy submitted map is ignored; the UI field is display-only and omitted from
submission. Preserve configuration precedence and absent-map `None`. This
restores the intended Portland parameterization without changing raster values,
scalar/monthly settings, defaults, formulas, or dataset selection.
ADR applicability: no numerical parameterization change is proposed; a change
to raster/scalar/monthly values, mode selection, or precedence would require a
separate parameterization ADR before merge.

Rationale: read-only inputs submit and stale pages persist. Rejecting the old
field would break valid rebuilds; trusting the stored value perpetuates corruption.
Security impact is low, reducing client control over a configured path.

Required evidence: configured/unconfigured/stale/hostile payload and failed-parse
rollback tests, persisted reload, real spatial-input propagation, targeted live
repair with backups and lock/cache checks. Two independent reviews and their
disposition must precede implementation; checkpoint commit is pending.
