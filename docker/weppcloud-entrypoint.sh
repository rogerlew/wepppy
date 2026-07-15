#!/bin/sh

# Exit immediately if a command exits with a non-zero status or if an unset
# variable is referenced. Keep the entrypoint fail-fast so container start
# aborts when the bundle build does not succeed.
set -eu

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
PROJECT_ROOT=$(CDPATH= cd -- "${SCRIPT_DIR}/.." && pwd)
BUNDLE_SCRIPT="${PROJECT_ROOT}/wepppy/weppcloud/controllers_js/build_controllers_js.py"

DEFAULT_OUTPUT="${CONTROLLERS_JS_OUTPUT:-${PROJECT_ROOT}/wepppy/weppcloud/static/js/controllers-gl.js}"
EXTRA_OUTPUTS="${CONTROLLERS_JS_EXTRA_OUTPUTS:-}"
STATIC_SYNC_DIR="${STATIC_ASSET_SYNC_DIR:-}"
VENDOR_SOURCE="${PROJECT_ROOT}/wepppy/weppcloud/static/vendor"

echo ">>> Building controllers-gl.js bundle via ${BUNDLE_SCRIPT}..."
python "${BUNDLE_SCRIPT}" --output "${DEFAULT_OUTPUT}"
echo ">>> controllers-gl.js bundle written to ${DEFAULT_OUTPUT}."

if [ -n "${EXTRA_OUTPUTS}" ]; then
  echo ">>> Replicating controllers-gl.js bundle to extra targets..."
  for target in ${EXTRA_OUTPUTS}; do
    target_dir=$(dirname "${target}")
    mkdir -p "${target_dir}"
    cp "${DEFAULT_OUTPUT}" "${target}"
    echo "    -> ${target}"
  done
fi

if [ -n "${STATIC_SYNC_DIR}" ]; then
  if [ -d "${VENDOR_SOURCE}" ]; then
    echo ">>> Syncing static vendor assets to ${STATIC_SYNC_DIR}..."
    mkdir -p "${STATIC_SYNC_DIR}"
    rm -rf "${STATIC_SYNC_DIR}/vendor"
    cp -a "${VENDOR_SOURCE}" "${STATIC_SYNC_DIR}/"
  else
    echo ">>> Warning: vendor source directory ${VENDOR_SOURCE} not found; skipping sync."
  fi
fi

echo ">>> controllers-gl.js bundle ready."

echo ">>> Validating wepppyo3 import..."
python - <<'PY'
import hashlib
import inspect
import os
from pathlib import Path

mount_release = "/workdir/wepppyo3/release/linux/py312"
fallback_release = "/opt/vendor/wepppyo3/release/linux/py312"
mount_package = f"{mount_release}/wepppyo3"
fallback_package = f"{fallback_release}/wepppyo3"

try:
    import wepppyo3  # type: ignore
    import wepppyo3.wepp_interchange as wepp_interchange  # type: ignore
except Exception as exc:
    print(">>> ERROR: unable to import the required wepppyo3 interchange release.")
    print(f"    exception: {type(exc).__name__}: {exc}")
    print(f"    mount release exists: {os.path.isdir(mount_release)} ({mount_release})")
    print(f"    mount package exists: {os.path.isdir(mount_package)} ({mount_package})")
    print(f"    fallback release exists: {os.path.isdir(fallback_release)} ({fallback_release})")
    print(f"    fallback package exists: {os.path.isdir(fallback_package)} ({fallback_package})")
    raise

required = {
    "catalog_scan",
    "hillslope_ebe_files_to_parquet",
    "hillslope_element_files_to_parquet",
    "hillslope_loss_files_to_parquet",
    "hillslope_pass_files_to_parquet",
    "hillslope_soil_files_to_parquet",
    "hillslope_wat_files_to_parquet",
    "watershed_chan_peak_to_parquet",
    "watershed_chanwb_to_parquet",
    "watershed_chnwb_to_parquet",
    "watershed_ebe_to_parquet",
    "watershed_loss_to_parquet",
    "watershed_pass_cli_hint",
    "watershed_pass_to_parquet",
    "watershed_soil_to_parquet",
    "watershed_tc_out_to_parquet",
}
missing = sorted(name for name in required if not callable(getattr(wepp_interchange, name, None)))
if missing:
    raise RuntimeError(f"incomplete wepppyo3 interchange API; missing: {', '.join(missing)}")

extension = Path(wepp_interchange.wepp_interchange_rust.__file__).resolve()
module_paths = (
    Path(inspect.getfile(wepppyo3)).resolve(),
    Path(inspect.getfile(wepp_interchange)).resolve(),
    extension,
)
outside_mount = [str(path) for path in module_paths if not str(path).startswith(f"{mount_release}/")]
if outside_mount:
    raise RuntimeError(
        "development stack requires the bind-mounted wepppyo3 release; "
        f"unexpected origins: {outside_mount}"
    )

artifact_sha256 = hashlib.sha256(extension.read_bytes()).hexdigest()
print(f">>> wepppyo3 interchange import OK: {extension}")
print(f">>> wepppyo3 interchange SHA256: {artifact_sha256}")
PY

echo ">>> Validating whitebox_tools import..."
python - <<'PY'
import os

mount_wbt = "/workdir/weppcloud-wbt/WBT"
fallback_wbt = "/opt/vendor/weppcloud-wbt/WBT"
mount_module = f"{mount_wbt}/whitebox_tools.py"
fallback_module = f"{fallback_wbt}/whitebox_tools.py"

try:
    import whitebox_tools  # type: ignore
except Exception as exc:
    print(">>> ERROR: unable to import whitebox_tools.")
    print(f"    exception: {type(exc).__name__}: {exc}")
    print(f"    mount WBT dir exists: {os.path.isdir(mount_wbt)} ({mount_wbt})")
    print(f"    mount module exists: {os.path.isfile(mount_module)} ({mount_module})")
    print(f"    fallback WBT dir exists: {os.path.isdir(fallback_wbt)} ({fallback_wbt})")
    print(f"    fallback module exists: {os.path.isfile(fallback_module)} ({fallback_module})")
    raise

module_path = getattr(whitebox_tools, "__file__", "<namespace>")
print(f">>> whitebox_tools import OK: {module_path}")
if str(module_path).startswith(fallback_wbt):
    print(">>> Warning: using baked whitebox_tools fallback from image (bind mount missing or incomplete).")
PY

# Replace the shell with the primary process to preserve signal handling.
exec "$@"
