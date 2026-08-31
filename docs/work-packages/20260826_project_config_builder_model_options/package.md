# Project Config Builder Model Options

**Status**: Open (2026-08-27)
**Timezone**: UTC

## Overview

Extend the project Config Builder with a WhiteboxTools-only Multiple OFE
watershed representation and an explicit WEPP binary version. The generated
project configuration must persist both selections and reject incompatible
combinations server-side.

## Scope

Included work is the project-owned-config and feature-registry canonical
contract amendment, registry/schema/resolver changes, Builder UI dependency
behavior, manifest provenance, run-header Preview derivation, and focused
regression coverage. Locale expansion, dynamic discovery of arbitrary binaries,
runtime editing of an existing project, and production deployment are out of scope.

## Success Criteria

- [ ] Single OFE remains available with TOPAZ and WhiteboxTools.
- [ ] Multiple OFE is available only with WhiteboxTools and writes
  `[wepp] multi_ofe = true`.
- [ ] Users choose a registered WEPP binary version and the generated config
  writes `[wepp] bin`.
- [ ] Server validation rejects invalid backend/representation/binary tuples.
- [ ] UI and backend regression tests pass without weakening existing creation
  or authentication boundaries.
- [ ] Every Builder-created project presents Preview maturity in its run header.

## Parameterization ADR Gate

- **Parameterization change present**: yes
- **ADR required**: yes
- **ADR link**: `docs/adrs/ADR-0046-config-builder-wbt-and-wepp-260803-defaults.md`
- **Decision provenance captured**: yes; operator requested the behavior in the
  2026-08-27 Codex session.

## Security Impact and Review Gate

- **Security impact triage**: low
- **Dedicated security review required**: no
- **Triage rationale**: an allowlisted basename now reaches the existing
  executable resolver; arbitrary paths remain prohibited and authentication,
  queue, and execution mechanics remain unchanged.

## Related Packages

- **Depends on**: [Project Config Builder UI](../20260804_project_config_builder_ui/package.md)
- **Related**: [Project Config Registry Serializer](../20260804_project_config_registry_serializer/package.md)

## References

- `docs/schemas/project-owned-config-contract.md`
- `docs/standards/contract-first-change-standard.md`
- `docs/adrs/ADR-0046-config-builder-wbt-and-wepp-260803-defaults.md`
- `wepppy/weppcloud/feature_registry/specification.md`
- `wepppy/weppcloud/routes/run_0/run_0_bp.py` - run-header Preview derivation
- `wepppy/nodb/config_builder/`
- `wepppy/weppcloud/templates/config_builder.htm`
