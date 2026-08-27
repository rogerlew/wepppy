# ADR: Config Builder WBT and WEPP 260803 Defaults

Status: Accepted
Date: 2026-08-27

## Decision Provenance

- **Decision Venue**: active Codex development session, 2026-08-27 04:00 UTC.
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
pair.

## Decision

New Config Builder projects default to WhiteboxTools (`wbt`), Single OFE, and
`wepp_260803`. The initial binary choices are `wepp_dcc52a6` and
`wepp_260803`. Multiple OFE is a conservative Builder V1 option available only
with WhiteboxTools and `wepp_260803`. Existing projects and shared Interfaces
presets are not migrated or changed.

Every Config Builder project is classified Preview. This maturity label
communicates that the expanded model-input matrix has not completed production
promotion.

## Rationale

The operator selected the deployed WhiteboxTools and `wepp_260803` path as the
default for new Builder work. Explicit registered defaults make the choice
reviewable, persist it in `config.cfg` and `config-manifest.json`, and prevent
host filesystem contents or lexical ordering from changing model behavior.

## Alternatives Considered

Keeping TOPAZ and `wepp_dcc52a6` as defaults was rejected because it does not
match the operator-selected path for new Builder projects. Exposing every
installed executable was rejected because historical and experimental files
are not a curated compatibility contract. Inferring a compatible binary after
submission was rejected because silent model-selection substitution would
obscure provenance.

## Evidence

- Contract checkpoint:
  `docs/work-packages/20260826_project_config_builder_model_options/artifacts/20260827_contract_decision.md`.
- Existing deployed binary pair:
  `wepp_runner/bin/wepp_260803` and `wepp_runner/bin/wepp_260803_hill`.
- Required acceptance evidence: direct execution of both registered binary
  pairs, a Forest WBT Multiple OFE preparation/run with `wepp_260803`, and a
  Forest Single OFE run with each exposed binary before registry exposure.

## Risk and Rollback Notes

Different WEPP binaries can produce different scientific outputs. WhiteboxTools
and TOPAZ can also delineate different watershed geometry. Preview maturity,
explicit review text, immutable manifest provenance, and the Forest execution
matrix make that difference observable.

Rollback removes the new registry defaults and choices for future Builder
creation. It does not rewrite flattened configs already created with
`wepp_260803`; changing existing projects requires separately authorized
remediation. Failure of executable, preparation, or representative-run evidence
blocks exposure and retains the previous Builder implementation.

## Consequences

New Builder projects intentionally differ from the former inherited defaults.
Tests must assert the defaults directly and must not derive them from registry
ordering. Existing runs and Interfaces presets preserve their recorded behavior.
