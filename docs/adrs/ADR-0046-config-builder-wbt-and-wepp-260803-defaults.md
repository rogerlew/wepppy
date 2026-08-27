# ADR: Config Builder Model and Landuse-Modification Defaults

Status: Accepted
Date: 2026-08-27

## Decision Provenance

- **Decision Venue**: active Codex development sessions, 2026-08-27 04:00 UTC
  and 2026-08-27 06:00 UTC.
- **Participants Present**: project operator and Codex.
- **Decision Owner**: project operator.
- **Implementer**: Codex.

## Context

The initial Config Builder inherited TOPAZ and `wepp_dcc52a6` from shared
defaults and exposed only Single OFE. Adding an explicit delineation and WEPP
binary selection requires deterministic defaults; relying on component sort
order would make a scientifically material choice accidental.

## Change Summary

Previously, new Builder configs inherited TOPAZ and `wepp_dcc52a6` and had no
explicit binary selection. After this decision, new Builder configs explicitly
default to WhiteboxTools and `wepp_260803`; Single OFE remains the default
representation, while Multiple OFE is available only with that backend/binary
pair. Builder configs previously inherited
`landuse.enable_landuse_change = false` from shared defaults; new Builder
configs now explicitly set it to `true` through the selected landuse component.

## Decision

New Config Builder projects default to WhiteboxTools (`wbt`), Single OFE, and
`wepp_260803`. Binary choices are the complete list returned by the canonical
runtime provider `wepp_runner.wepp_runner.get_linux_wepp_bin_opts()`. Multiple
OFE is a conservative Builder V1 option available only with WhiteboxTools and
`wepp_260803`. Existing projects and shared Interfaces presets are not migrated
or changed.

Every Config Builder project is classified Preview. This maturity label
communicates that the expanded model-input matrix has not completed production
promotion.

New Config Builder projects also enable landuse modification. The selected
landuse component owns and writes this Builder-scoped value. Existing projects,
shared defaults, and Interfaces presets are not migrated or changed.

## Rationale

The operator selected the deployed WhiteboxTools and `wepp_260803` path as the
default for new Builder work. Explicit registered defaults make the choice
reviewable and persist it in `config.cfg` and `config-manifest.json`. Binary
availability intentionally follows the canonical runtime provider, while the
default never follows provider or lexical ordering.

The Builder is intended to expose its configured landuse workflow, including
post-delineation landuse edits. Writing the capability in the registered
landuse component makes that behavior explicit in generated configuration and
component provenance without broadening the shared default.

## Alternatives Considered

Keeping TOPAZ and `wepp_dcc52a6` as defaults was rejected because it does not
match the operator-selected path for new Builder projects. A separate
hard-coded Builder binary allowlist was initially selected, then superseded by
the operator's requirement that Builder use the complete canonical provider
list. Inferring a compatible binary after submission remains rejected because
silent model-selection substitution would obscure provenance.

Keeping landuse modification disabled was rejected because it unnecessarily
hides the Builder run-page editing workflow. Changing shared `_defaults.cfg`
was rejected because it would alter unrelated legacy and Interfaces configs.

## Evidence

- Contract checkpoint:
  `docs/work-packages/20260826_project_config_builder_model_options/artifacts/20260827_contract_decision.md`.
- Canonical availability provider:
  `wepp_runner.wepp_runner.get_linux_wepp_bin_opts()`.
- Required acceptance evidence: direct role resolution and representative
  execution for every provider-exposed binary, a Forest WBT Multiple OFE
  preparation/run with `wepp_260803`, and a Forest Single OFE run with each
  exposed binary before registry exposure.

## Risk and Rollback Notes

Different WEPP binaries can produce different scientific outputs. WhiteboxTools
and TOPAZ can also delineate different watershed geometry. Preview maturity,
explicit review text, manifest provenance, and the Forest execution matrix make
that difference observable. The provider's `latest` entry is intentionally a
mutable alias: its resolved target is recorded at creation, but future runs may
resolve a newer target. Users requiring immutable-release reproducibility must
select a concrete binary value.

Rollback removes the new registry defaults and choices for future Builder
creation. It does not rewrite flattened configs already created with
`wepp_260803`; changing existing projects requires separately authorized
remediation. Failure of executable, preparation, or representative-run evidence
blocks exposure and retains the previous Builder implementation.

Landuse modification changes only the availability of an explicit user action;
it does not rewrite landuse automatically. Rollback changes the registered
landuse component value back to false for future Builder projects and does not
rewrite existing flattened configs.

## Consequences

New Builder projects intentionally differ from the former inherited defaults.
Tests must assert the defaults directly and must not derive them from registry
ordering. They also expose the Modify Landuse control. Existing runs and
Interfaces presets preserve their recorded behavior.
