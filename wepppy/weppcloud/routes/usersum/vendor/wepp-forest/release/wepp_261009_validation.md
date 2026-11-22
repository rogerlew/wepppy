# WEPP 261009 validation and promotion status

2026-10-09. Model and general PASS compatibility implementation are complete.
The manual replay conflict is resolved: Roger reaffirmed retirement and the
committed-resource gate rule. The paired binaries and sidecars are vendored
in WEPPpy, with host/container smokes and runtime provenance passing.
Deployment additionally requires Roger's mutation and disturbed studies.

## Confirmed Gates

- System gfortran dated build from default-branch source 5a01758b7 succeeds.
- Both host smokes pass using maintained committed fixtures.
- Permanent hillslope watchlist: 12/12 pass.
- Forest pytest: 155 pass, two existing tarfile deprecation warnings.
- ELF interpreter and system runtime provenance checks pass for both binaries.
- Rust reader/composition: 104 unit plus 17 integration tests pass.
- Installed native-reader Python suite: 139 pass.
- WEPPpy Roads/AgFields metadata/controller tests: 77 pass.
- WEPPpy interchange/runner/output/Concept1 tests: 118 pass, one skip.
- Post-vendor runner/interchange/output/startup-pin tests: 124 pass, one skip.
- Both vendored host and container smokes pass with committed inputs.
- Native reader import and pinned-hash preflight pass on host and dev container.
- Scoped Markdown lint and ablation artifact policy pass.

Supplementary external-fixture evidence: nine fresh original-trigger/control
runs pass with observer identity; Ksat-35 peaks remain 1.605/2.038 mm/h and
no-return controls remain unchanged. These are not mandatory release gates.

The full WEPPpy sweep first stopped at an obsolete expected interchange hash
(399 passed, 28 skipped). That expectation was updated with the coordinated
artifact pin. The second sweep was deliberately interrupted after 14m32s while
executing unrelated Rosetta soil-generation integration coverage, with 2,375
passed and 48 skipped. SIGINT became a DuckDB Query interrupted exception in
the active test, so pytest reported one failed test caused by that interruption.
This sweep is incomplete, not a pass. The interrupted case passed separately
through wctl (one test, 8.35 seconds);
no scientific study or test threshold is substituted for the omitted remainder.

Archived evidence retains its original bytes, including CRLF CSV and historical
patch whitespace. Scoped .gitattributes prevent normalization; staged checksum
verification checks the actual Git blobs, not just working-tree files.

## Generated Outputs

External evidence root: /wc1/holdouts/wepp-261009-release-validation-v2.
The standalone tool tools/validate_pass_v3_release.py records fixture hashes,
build/reader identities, individual run receipts and composition results.
Its first attempt stopped before simulation because an earlier run rewrote
chntyp.txt; the second resolved every input against frozen hashes from the
retained fixture copies. The failed partial root is preserved without promotion.

All 140 hills were freshly generated for the complete 45-year record with the
release hillslope binary. Their 980 outputs exactly match the accepted candidate.
The plain watershed's pass, EBE, plot, loss, soil and channel-water-balance files
also match exactly. Comparisons did not substitute older passes into simulations.

The two additional native interface replays use those fresh files:

- Roads: add H1 to itself, deliberately doubling its supplied runoff volume
  from 195,011.111 to 390,022.222 m3. Complete watershed run succeeds.
- AgFields: combine two H1 representations weighted 0.3 and 0.7. Supplied runoff
  remains 195,011.111 m3. Complete watershed run succeeds.

These are composition-interface controls, not actual disturbed or Roads scenario
validation. Unit tests also cover distinct active/pure-return/inactive components,
unequal areas, zero-area sources and version mismatch. All three generated
watershed PASS files convert with 2,301,320 records and zero rejections each.
Hillslope conversion has zero rejections. Compact receipts and gate logs are in
[the evidence directory](wepp_261009_validation/); large raw runs stay external.

## Retired Gate and Resource Policy

Roger reaffirmed on 2026-10-09 that reconciled-condenser is retired. Required
gates must not depend on uncommitted resources. The rule is now explicit in
forest AGENTS and WEPPpy's runner guide and binary lifecycle policy. No absent
fixture is reported as passed. Fresh external watershed/composition studies
remain supplementary evidence, not replacement mandatory private-resource gates.

WEPPpy's smoke inputs are committed in 906b32fc7, copied from the bounded
forest fixture. Host and container gates share staging and completion checks.
The historical dual-binary forest regression uses committed WEPPpy artifacts
wepp_260419 and wepp_260420 (present in WEPPpy commit 8b1b29fd5); it is historical
coverage, not validation of the new model's runtime.

## Reproduction Commands

Build: TARGET_TAG=261009 COMPILER=/usr/bin/gfortran
tools/build_wepp_dated_release.sh; then make prepare_watershed_includes in src.
Forest: python -m pytest -q; tools/smoke_wepp_binary_host.sh on each release
binary; tools/run_hillslope_watchlist.py --binary release/wepp_261009_hill;
tools/check_ablation_artifact_policy.py.
Runtime provenance: WEPPpy tools/check_wepp_binary_provenance.sh on both binaries.
Native: cargo test --offline -p wepp_interchange_rust and cargo build --release
--offline -p wepp_interchange_rust -j4, with PYO3_PYTHON pointing at the WEPPpy
venv and RUSTFLAGS='-C link-arg=-lpython3.12'.
WEPPpy test groups above ran through wctl run-pytest; the full sweep uses
wctl run-pytest tests --maxfail=1.
