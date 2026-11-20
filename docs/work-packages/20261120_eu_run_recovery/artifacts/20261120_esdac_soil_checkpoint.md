# ESDAC soil restoration implementation checkpoint

Starting revision `c2e6f4d1a4022b1ef7e3388fa0f5ab708530d1db`. The operator confirmed fixed, editable, automatically applicable project-wide subsoil defaults and approved the persistent warning above successful soil coverage on 2026-11-20 UTC. This checkpoint covers the fallback profile, warning, and the confirmed 7778 and repeated-member Disturbed defects. Implementation conformance is pending. Climate and land-use decisions stay in the broader package.

## Canonical amendments

- [ESDAC source, publish and format contract](../../../schemas/esdac-soil-source-contract.md)
- [Request inputs and exact field names](../../../schemas/request-payload-contract.md#gridded-esdac-subsoil-profile)
- [RQ lifecycle and accepted summary](../../../schemas/rq-controller-state-contract.md#gridded-esdac-soil-build-inputs)
- [Project ownership and source selection](../../../schemas/project-owned-config-contract.md#esdac-subsoil-build-settings)
- [Fixed preset and parameterization rationale](../../../adrs/ADR-0151-esdac-missing-subsoil-defaults.md)

Existing admission scopes, access, CSRF, read-only rules, providers, runtime identities, queue topology, report schema and native soil formats are preserved. Security impact is low. Six bounded scalars use the existing soil build endpoint. The validation and writer changes introduce no new path input, user-supplied comments or executable format.

## Valid runtime states

| State | Required outcome |
| --- | --- |
| New or legacy ESDAC project without saved profile | Show fixed preset without provider access. An omitted request uses it. |
| Saved profile or later in-page switch to gridded ESDAC | Show saved profile and serialize complete enabled fields only for the effective ESDAC path. |
| Non-ESDAC, single soil or incompatible source/representation | ESDAC fallback cannot run. Non-gridded modes hide and disable the fields. |
| Existing direct build or old job without snapshot | Existing call shape remains valid. Resolve applicable persisted/fixed values at build time. |
| Admitted job with snapshot | Retry consumes the same validated profile. Later requests cannot change that input. |
| Batch settings save without enqueue | Persist validated profile using the existing batch settings path. Snapshot at a subsequent queued admission where present. |
| Valid native profile, unused subsoil, exact six-source-zero missing profile | Preserve native and unused paths. Only the required exact missing material consumes the fallback, with degraded provenance. |
| Partial zeros, malformed metadata, invalid data in another material | Existing failures still apply. Preserve field-specific feedback. |
| A prior success followed by failure | A surviving accepted release retains its own summary and warning. If existing execution invalidates the release, clear the prior summary on reload. Rejection diagnostics belong to their own attempt. |
| 7778 transformed member with required expectations | Use exact final recognized pre-body writer block; validate physical records. Fail malformed or mismatched provenance with rebuild guidance. |
| Native metadata format, base copy or combined stack | Keep applicable native or numeric validation. Check transformed members before assembly. |

## Request and regression matrix

Omitted profile, complete JSON numeric profile and complete form decimal profile are supported. Partial, repeated, unknown reserved fields, blanks, Booleans, containers, nonfinite values, invalid fractions/density, and ineligible builder submissions fail before state changes. Enqueue conflicts and failures preserve prior state. Normal non-ESDAC and older API clients keep their call shape.

Use real soil generation with missing and accepted incident inputs, admitted and failed HTTP requests with state readback, concurrent and retried real job records, stable provenance across equivalent-file reuse, and parsed 7778 and native-metadata output controls. Test fresh and repeated same-key MOFE stacks, a previously generated member, a base copy and ambiguous or missing writer provenance. Verify the visible warning count against accepted .sol assignments on successful build, refresh and reload. Test an unsuccessful later build separately. Full deployment and both incident browser replays remain release acceptance.

## Review disposition

Two independent read-only reviewers initially confirmed exact six-zero eligibility for all 37 incident rejects, the missing provenance risk on equivalent-file reuse, effective source binding, and the version-specific Disturbed issue. One reviewer reproduced the same-key MOFE staging defect. Their follow-up reviews of the canonical draft required exact wire fields and tolerance, prior job and batch compatibility, stale receipt behavior, native-format coverage, and a fixed-preset receipt. The canonical amendments and this checkpoint record those outcomes. Review dates are 2026-11-20 UTC. The [study](20261120_esdac_same_unit_study.md) includes the raw six-field and fixed-preset results. Both independent reviewers reconfirmed the final soil checkpoint by 2026-11-20 09:43 UTC with no blocking findings. Clarified the nonblocking empty-profile and duplicate JSON points in the canonical contracts. ADR-0151 is accepted for this slice. Implementation conformance remains pending.
