# Release capability declarations

The dated release builder declares `features.mofe_supported` and
`features.single_user_defined_inputs_supported` in both role sidecars.
These are strict booleans. MOFE means multiple overland-flow elements.
The input-reader declaration covers WEPPcloud's single management/soil inputs:
management 98.4, soils 7777, 2006, 2006.2, 9002 and 7778, up to 32 OFEs.
It does not guarantee numerical stability for arbitrary parameterizations.

WEPPpy requires matching true declarations and executable SHA-256 identities
for new selections requiring these capabilities. Missing declarations mean
unknown support. Ordinary single-OFE availability does not require these flags.
Do not infer support from release dates or names.

`tools/generate_wepp_release_sidecar.py` requires explicit
`--mofe-supported`/`--no-mofe-supported` and
`--single-user-defined-inputs-supported`/`--no-single-user-defined-inputs-supported`.
The default-branch dated builder supplies both positive declarations. Reassess
these declarations if a future release removes either feature.

For existing releases, add `--refresh-capabilities` with the original binary,
role, release tag, source branch and source commit. Refresh validates immutable
identity, including repository and SHA-256, before modifying only these two
feature members. It preserves build time, PASS flags and validation history.
Refresh both roles together; copy the resulting sidecars unchanged to WEPPpy.
A capability-only remint does not rebuild or relabel executable bytes.

## 260803 and 261010 remint

Both roles of both releases now declare both features. Executable bytes and
original source/build provenance are unchanged. Native acceptance in WEPPpy
uses committed soil, management and climate resources: two releases, five soil
formats, and 1/2/32 OFEs (30 actual two-year hillslope executions), through the
real multi-OFE preparation worker. Source files remain unchanged and generated
loss outputs are nonempty and finite. The reproducible driver and receipts are
in WEPPpy `docs/work-packages/20261012_wepp_executable_capabilities/artifacts/`;
its committed fixture baseline is `cf2ad6d7874b25377f529550b41cd46fc1f1e74f`.
Generator preservation, idempotence and identity-rejection tests are in
`tests/test_release_sidecar_capabilities.py`.
