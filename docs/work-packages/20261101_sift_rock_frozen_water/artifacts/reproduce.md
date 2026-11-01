# Reproduction and evidence locations

Run from the WEPPpy repository. The production repair uses the canonical
container and requires its existing numerical/geospatial dependencies. No new
formatter dependency is installed.

## Application and generated soils

    wctl run-pytest tests/locales/canada/bc/soils/test_sift_rock_basis.py tests/locales/earth/soils/test_isric_rock_basis.py tests/wepp/soils/test_rock_fragments.py tests/soils/test_horizon_boundary.py -q --maxfail=1
    wctl run-pytest tests --maxfail=1
    wctl check-test-stubs
    python3 tools/check_broad_exceptions.py --enforce-changed --base-ref origin/master wepppy/locales/canada/bc/soils/sift/sift.py

Set `STUDY` to a fresh private destination and use absolute paths visible inside
the container. Each producer refuses an existing destination.

    wctl exec -T weppcloud /opt/venv/bin/python -B /workdir/wepppy/docs/work-packages/20261101_sift_rock_frozen_water/artifacts/produce_sift_fixtures.py --repo /workdir/wepppy --out "$STUDY/sift-artifacts"

The synthetic source records are defined by the committed regression helper.
This exercises the actual SIFT builder, Rosetta, serializer and canonical parser.
The supplied local BC geodatabase path is unavailable; these records do not
represent a deployed-data extraction.

## Native generated-soil histories

The retained complete observer/runtime bundle is required; the runner verifies
its binary, all 978 build members and all 16 original inputs. Without access to
that private archive, full native replay is unavailable. Do not substitute a
different binary and claim the same observation identity.

    python3 -B docs/work-packages/20261101_sift_rock_frozen_water/artifacts/read_sift_native.py --repo "$PWD" --fixtures "$STUDY/sift-artifacts" --out "$STUDY/sift-native"
    python3 -B docs/work-packages/20261101_sift_rock_frozen_water/artifacts/read_sift_outputs_v2.py --runs "$STUDY/sift-native" --out "$STUDY/sift-readback-v2"

The original runner is deliberately preserved: all three native processes finish,
but its validator rejects decorative stars in the loss report. The second,
independently reviewed reader recognizes only the known decoration contexts,
retains every original numerical check, and verifies hash/size/mtime nonmutation
of every retained file. It does not rerun native histories. This preserved
verification failure is not a model failure or changed acceptance threshold.

## Complete frozen-water routine

Use the exact source checkout whose 13 source/include identities match
frozen-design-source-bindings.json. Authored driver and runner are public;
legacy native source and built objects remain private.

    python3 -B docs/work-packages/20261101_sift_rock_frozen_water/artifacts/run_frozen_campaign.py --source /workdir/wepp-forest-release-20261009/src --out "$STUDY/frozen-campaign"

The runner pins compiler/PATH, compiles the complete unchanged FRWATC, executes
all 29 fresh processes, and retains each input, stdout/stderr and disposition.
Eighteen normal controls must close. Eleven threshold cases characterize
behavior; five expose discrepancies and are not conservation passes. Their
successful process exit is separate from physical acceptance. A future fix
must retain these counterexamples and pass newly reviewed mutation gates.

## Retention

Current raw tree: out/sift-rock-frozen-water-20261101. Baseline failures, generated
files, native histories, reviewer readbacks and test logs are retained there.
Archive receipt and publication manifest identify the completed frozen packet.
Prior 495-file source/scalar and 353-file rock-representation trees have been
rechecked against their manifests without missing, changed or extra members.
Native source-free incident: docs/ablation/20261101_sift_frozen_mapping in the
native repository. No production source, release binary or live run is modified
there; its status remains active research because no conservation fix is promoted.
