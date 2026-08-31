# WP12C Checkpoint Scope Deviation

**Amendment**: `PC-23/WP12C-20260827-1`
**Ratified checkpoint**: `bb1745fd8`
**Implementation commit where discovered**: `280cf7e84`
**Accepted candidate**: `b31eeb625`
**Recorded**: 2026-08-27
**Classification**: incomplete changed-consumer enumeration; no normative
behavior or authority-source expansion

## Deviation

The ratified contract decision described its changed implementation-consumer
list as exact, but the implementation diff from `bb1745fd8` to `280cf7e84`
also changed these two consumers:

- `wepppy/nodb/project_config_capabilities.py` extends the side-effect-free
  stored capability reader and validator from schema v2 to schema v2/v3. It
  cannot add choices outside the stored graph and performs no authentication,
  persistence, queue, or NoDb mutation. Its preexisting schema-v1 named-preset
  snapshot helper remains pure and was not broadened by WP12C.
- `wepppy/nodb/locales/__init__.py` reexports the typed station-database and
  multi-profile capability symbols. It contains no authority logic,
  authentication, I/O, or mutation.

The exact `280cf7e84` hunks are required consumer wiring: the first parses and
validates the schema-v3 graph stored by WP12C, and the second makes the already
owned locale symbols available through the package interface. Authority remains
owned only by the ratified locale profiles, domain catalogs, runtime maps, and
canonical WEPP provider. Neither file is a new authority source.

This omission was discovered during implementation review by comparing the
ratified boundary with the actual changed-file set. It does not authorize a new
locale, dataset, default, route, permission, mutation, Forest action, schema-v3
run, or production action.

## Operator Acceptance

On 2026-08-27, the operator stated:

> Accept the standalone audit correction adding
> project_config_capabilities.py as a stored-authority reader and
> locales/__init__.py as export-only to WP12C’s changed-consumer list,
> preserving all existing commits and carrying a scope-vs-changed-files check
> into WP12.

The existing checkpoint and implementation commits remain unchanged so the
repository preserves the true chronology. This standalone correction records
the accepted deviation rather than rewriting the ratified checkpoint.

## Independent Control Confirmation

Correctness review at `b31eeb625` confirmed that `locales/__init__.py` is
export-only and the schema-v2/v3 paths in
`project_config_capabilities.py` are side-effect-free stored-authority readers
that cannot broaden stored axes. Security review independently confirmed that
the files add no authentication, write, enqueue, registry-loading, or NoDb
mutation behavior. Governance re-review of this correction remains required
before any Forest restart.

## Prevention and WP12 Handoff

WP12 must compare the ratified source/consumer boundary against
`git diff --name-only` for the full implementation range before accepting the
release candidate. Every changed production file must be classified as an
authority source, consumer, compatibility surface, or unrelated excluded
change. Any omission requires an explicit, chronology-preserving correction
before production promotion.
