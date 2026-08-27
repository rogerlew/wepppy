# Contract Decision: Builder Representation and WEPP Binary Options

**Starting implementation revision**: `b53b767b667481cc6a0052d11a386f2ef450e2ed`
**Operator approval**: Explicitly requested 2026-08-27 in the active Codex session.
**Implementation conformance**: Pending.

## Applicable Canonical Contracts

- `docs/schemas/project-owned-config-contract.md`, sections 7.2, 7.2.1,
  7.4, 7.5, 10, and 15.
- `docs/standards/contract-first-change-standard.md`.
- `wepppy/weppcloud/feature_registry/specification.md`, Config Registry runtime
  semantics and run-header maturity presentation.
- `docs/adrs/ADR-0046-config-builder-wbt-and-wepp-260803-defaults.md`.

## Normative Delta

The initial registered family gains `multiple-ofe` and registered WEPP binary
components. `multiple-ofe` is valid only when the delineation backend is `wbt`
and the WEPP binary is `wepp_260803`. `single-ofe` remains valid with `topaz` or
`wbt` and with either initial binary. WhiteboxTools and `wepp_260803` are the
explicit defaults. Builder submissions explicitly select a WEPP binary, server
validation enforces the complete tuple, and generated `config.cfg` files persist
`[wepp] multi_ofe` and `[wepp] bin`. Every Builder-created project is presented
as Preview in the run header. New Builder configs explicitly persist
`[landuse] enable_landuse_change = true`; the selected landuse component owns
that key, and the run page exposes its Modify Landuse control.

The initial binary registry contains `wepp_dcc52a6` and `wepp_260803` only.
Runtime filesystem discovery does not broaden the Builder registry.

## Rationale and Rejected Alternatives

WhiteboxTools-only Multiple OFE is a conservative Builder V1 eligibility policy,
not a claim that the runtime cannot build TOPAZ Multiple OFE projects; existing
TOPAZ MOFE presets remain unchanged. WEPP binary selection is material model provenance
and belongs in the immutable creation snapshot. Arbitrary installed-binary
discovery was rejected because it would make registry revisions and accepted
payloads vary by host. An unconstrained Multiple OFE binary was rejected because
the operator selected the deployed `wepp_260803` release for Builder Multiple
OFE rather than claiming all later binaries are interchangeable.

## Compatibility and Security

There is no migration. Existing runs, configs, and manifests remain unchanged,
readable, and runnable. Update preview/apply is explicitly unavailable for
pre-change Builder manifests because their immutable parent chain lacks a binary
component. The new field is required only for new Builder submissions after the
registry revision changes. Stable binary IDs are fixed basename tokens without
path separators; validation confirms matching executable watershed and
hillslope binaries before registry exposure. The selected allowlisted ID later
reaches the existing executable resolver, but authentication, CSRF, CAP, and
queue boundaries do not change. Security impact is low.

The landuse-modification default is scoped to Builder output. Shared defaults
and Interfaces presets remain unchanged, and enabling the control performs no
automatic landuse mutation.

Removing a binary from the registry prevents new selection and does not rewrite
already flattened projects. Withdrawing it from existing projects requires a
separately authorized remediation.

## Regression Evidence

- Registry tests prove component ownership, references, and deterministic revision.
- Resolver tests prove every valid backend/representation/binary tuple and reject
  TOPAZ plus Multiple OFE and legacy-binary plus Multiple OFE.
- Snapshot/API tests prove `wepp_binary` is required and field-addressable.
- Generated-config tests parse actual serialized bytes and assert both WEPP keys.
- Direct unmocked checks prove both executable pairs exist and execute; Forest
  acceptance prepares and runs a representative WBT Multiple OFE project with
  `wepp_260803` and a Single OFE project with each exposed binary.
- Controller tests prove dependent options clear visibly and cannot remain in
  submitted payloads after an upstream selection changes.
- Existing Interfaces and Builder authentication tests remain green.
- Run-header tests prove a valid Builder manifest with token `config` presents
  Preview and malformed or non-Builder manifests do not invent that provenance.

## Review Disposition

The first review round rejected the draft because it inferred binary defaults,
misstated WBT as a technical dependency, omitted legacy-update and maturity
behavior, and lacked execution evidence. The operator then explicitly selected
WhiteboxTools and `wepp_260803` defaults and classified every Builder project as
Preview. The amendment now treats WBT-only MOFE as conservative Builder policy,
defines old-manifest update unavailability, adds executable containment and
Forest execution evidence, and completes the canonical component surfaces.
The final independent governance and correctness reviews found no remaining
issues. Their artifacts are `20260827_governance_review.md` and
`20260827_correctness_contract_review.md`. The checkpoint is approved for its
standalone ancestor commit and bounded implementation.
