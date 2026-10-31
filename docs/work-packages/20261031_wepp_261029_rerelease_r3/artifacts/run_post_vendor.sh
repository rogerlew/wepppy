#!/usr/bin/env bash
set -euo pipefail
cd /workdir/wepppy
raw=/workdir/wepppy/out/roads-native-funding-20261031/r3-integration
mkdir -p "$raw"
tools/check_wepp_binary_provenance.sh wepp_runner/bin/wepp_261029 wepp_runner/bin/wepp_261029_hill > "$raw/provenance.log" 2>&1
for role in wepp_261029 wepp_261029_hill; do
 tools/smoke_wepp_binary_host.sh "wepp_runner/bin/$role" > "$raw/host-$role.log" 2>&1
 tools/smoke_wepp_binary_in_container.sh "wepp_runner/bin/$role" > "$raw/container-$role.log" 2>&1
done
wctl run-pytest tests/wepp_runner/test_run_hillslope_retries.py tests/wepp/test_wepp_runner_outputs.py tests/wepp_runner/test_binary_capabilities.py tests/nodb/test_wepp_binary_policy.py tests/nodb/test_project_config_builder_snapshot.py tests/weppcloud/routes/test_usersum_bp.py tests/weppcloud/test_usersum_template_wiring.py --maxfail=1 > "$raw/targeted.log" 2>&1
wctl exec -T weppcloud env PYTHONPATH=/workdir/wepppy python /workdir/wepppy/docs/work-packages/20261031_wepp_261029_rerelease_r3/artifacts/verify_selected_watershed.py /workdir/wepppy/out/roads-native-funding-20261031/r3-selected-watershed > "$raw/selected-watershed.log" 2>&1
wctl exec -T weppcloud env PYTHONPATH=/workdir/wepppy python /workdir/wepppy/docs/work-packages/20261030_wepp_261029_release/verify_selected_release.py /workdir/wepppy/out/roads-channel-accounting-20261030/selected-r2-hill-inputs.zip /workdir/wepppy/out/roads-native-funding-20261031/r3-selected-hill > "$raw/selected-hill.log" 2>&1
