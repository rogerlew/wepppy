# Contract correctness review

Reviewer: independent correctness reviewer. Date: 2026-09-10.
Scope: proposed Builder SBS contract, ADR-0064, resolver/snapshot/update readers,
Ron/NoDb initialization and Disturbed event dependencies. Runtime review is
read-only. No tests or live-project mutations were performed; the full suite
was explicitly excluded.

## Finding: required management mapping is missing (high, contract resolved)

Enabling `disturbed` alone does not provide a working normal Disturbed workflow
for the default continental-US Builder selection. The NLCD profile writes only
the land-cover source and change capability; `_defaults.cfg` has no management
mapping. `Landuse.__init__` stores `_mapping=None`
(`wepppy/nodb/core/landuse.py:559`). Its mapping loader therefore reads
`wepppy/wepp/management/data/map.json`, whose 99 records lack `DisturbedClass`.

`Disturbed.on(LANDUSE_DOMLC_COMPLETE)` calls `remap_landuse`, which calls
`get_disturbed_key_lookup` before checking whether an SBS map exists
(`wepppy/nodb/mods/disturbed/disturbed.py:1544`, `:1576`). Accessing the missing
field raises `KeyError` during a normal landuse build, even without SBS. The
default map also lacks all nine required forest/shrub/grass burn classes.
The SBS upload browser path alone will not expose this failure.

Resolve the management-mapping contract before implementation: identify the
existing Disturbed-compatible mapping for each exposed land-cover source and
state its creation provenance and historical-update preservation policy.
`disturbed`, `c3s-disturbed`, `au-disturbed` and `eu-disturbed` tables provide
the required classes; existing `disturbed9002_wbt.cfg:21` explicitly selects
`disturbed`. Current Builder registry code already selects `c3s-disturbed` for
C3S sources (`wepppy/nodb/config_builder/registry.py:553`), but does not select
one for NLCD. Do not apply the NLCD mapping indiscriminately to other sources.
The existing-run repair must also establish whether `fair-division` already
has a compatible mapping, while respecting its controller-preservation scope.

The initial contract statement that management mapping remains unchanged
conflicted with this dependency. The amended canonical section and ADR-0064
now select existing source-compatible mappings explicitly: NLCD/EMAPR use
`disturbed`, CORINE uses `eu-disturbed`, Australian landuse uses `au-disturbed`,
and C3S retains `c3s-disturbed`. They assign the write and revision to the
landuse component, preserve historical populated values, permit an explicit
additive update for missing values, and authorize the named run's absent/default
mapping repair. This resolves the contract finding. Runtime closure requires
implementation and focused evidence; no Disturbed algorithm change is needed.

## Confirmed contracts and implementation obligations

- The owner explicitly authorized normal Disturbed adjustments without SBS.
  ADR-0064 correctly records that activation changes generated soil inputs,
  while retaining existing numerical routines and inherited `sol_ver=7778`.
- Keep `selections.mods` unchanged in `config_builder/snapshot.py:105`.
  Effective modules may be exactly `['disturbed', *selected_without_disturbed]`.
  `_assert_builder_congruence` must accept only the exact historical list or
  that ordered effective list. Preserve duplicate-selection rejection in the
  resolver and existing malformed-manifest checks.
- The existing capability-refresh payload already preserves current
  `nodb.mods` (`project_config_update.py:944`). Keep this behavior for historical
  projects; resolver evolution must not silently enable their modules.
- Adding a landuse-owned mapping/revision activates the existing refresh
  completeness check. `_assert_builder_refresh_completeness` currently rejects
  missing mapping before additive preview can propose it, while
  `_assert_builder_congruence` rejects a populated historical mapping that differs
  from the new target. Apply the documented narrow historical mapping policy in
  both checks; retain strict validation of unrelated selection-bearing values.
- Ron initializes every listed controller for new projects. Existing repairs
  must update the persisted module lists on Landuse and Soils, as these dispatch
  the two relevant events (`landuse.py:1291`, `soils.py:793`), along with the
  explicitly scoped core/project controllers. Updating Ron alone is insufficient.
- Reuse existing Disturbed state. Its constructor uses `os.mkdir` and resets
  its lookup file (`disturbed.py:905`, `:920`, `:988`). An orphan existing
  `disturbed/` directory must fail explicitly before any partial enablement,
  not be overwritten or passed to a newly permissive constructor.

## Disposition and residual coverage

Approve the amended contract checkpoint: no unresolved contract blocker remains.
This is not implementation signoff. Initialization-only tests cannot prove event integration:
focused validation should exercise the selected management mapping through
`get_disturbed_key_lookup`, a no-SBS landuse completion, and downstream soil
artifact generation. Validate every exposed source's mapping compatibility,
plus historical config-update preservation and idempotent existing-state repair.
Browser upload/classification/removal remains required execution evidence.
