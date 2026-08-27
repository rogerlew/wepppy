# Binary Provider Contract Decision

## Starting revision

`a4877628676388817b4a68671f6144e91d174683`

## Authority and decision

On 2026-08-27 the project operator explicitly required Config Builder to expose
the whole list supplied by the default WEPP binary-list provider and to remove
the "legacy parity" annotation. This supersedes the package's earlier
two-binary allowlist decision.

## Applicable canonical contracts

- `docs/schemas/project-owned-config-contract.md`, sections 7.2.1, 7.4, 8.2,
  and 15.
- `docs/adrs/ADR-0046-config-builder-wbt-and-wepp-260803-defaults.md`.

## Normative delta

Builder binary availability comes from
`wepp_runner.wepp_runner.get_linux_wepp_bin_opts()` and preserves its complete
unique output, including `latest`. `wepp_260803` remains the explicit default.
Multiple OFE remains limited to WBT plus `wepp_260803`. Labels do not add
lifecycle claims absent from provider output. Missing default availability is
an explicit registry failure.

The registry loader has a bounded provider-backed exception to the TOML-only
component rule. Provider values and the SHA-256 identities of their
role-resolved watershed and hillslope executables enter the opaque registry
revision. Missing or unusable role targets invalidate Builder binary
availability atomically. `latest` remains a mutable alias in generated config;
its creation-time role identities are manifest provenance, not a promise that
subsequent runs use the same executable bytes.

## Compatibility and state matrix

- Populated unique provider values: expose all values for Single OFE.
- Duplicate provider values: expose each value once.
- Empty output or missing `wepp_260803`: fail explicitly; do not substitute.
- Unknown or hostile submitted value: reject because it is absent from the
  runtime registry.
- Existing manifests: remain readable and runnable with no migration.
- Multiple OFE with any non-`wepp_260803` value: reject and clear visibly.
- Provider output or `latest` target changes after description: stale-schema
  409, no project creation, reload required.

Availability becomes deployment-dependent by explicit operator decision. No
data migration, new dependency, security-boundary change, or queue wiring
change is introduced. Security impact remains low.

## Proposed regression evidence

- Patch provider output and prove every supplied value is serialized by the
  Builder description and accepted for Single OFE.
- Prove the default remains `wepp_260803` independent of provider ordering.
- Prove `latest` is included and no "legacy parity" text is rendered.
- Preserve server rejection and UI clearing for Multiple OFE with other values.
- Prove one invalid or unusable provider value fails the entire binary registry
  rather than filtering the value.
- Prove provider-set and role-identity changes alter `registry_revision`, make
  the prior payload return stale-schema 409, and create no project.
- Prove a `latest` selection retains `latest` in generated config while its
  manifest records the creation-time role identities.
- Execute the real provider-wide watershed and hillslope role gate on Forest,
  plus the WBT Multiple OFE combination.

Implementation conformance is pending the standalone checkpoint and subsequent
implementation commit.
