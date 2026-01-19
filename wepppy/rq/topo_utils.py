from __future__ import annotations

import logging
import shutil
from pathlib import Path

from whitebox_tools import WhiteboxTools

LOGGER = logging.getLogger(__name__)


def _prune_stream_order(
    flovec_path: Path,
    netful_path: Path,
    passes: int,
    *,
    overwrite_netful: bool = True,
) -> None:
    """Prune first-order streams from the network.

    Creates intermediate files:
    - netful.strahler.tif (initial Strahler order raster)
    - netful.strahler_pruned_*.tif (order rasters for intermediate passes)
    - netful.pruned_{N}.tif (binary stream map from the final pass)

    When overwrite_netful is True, the final pruned result is copied to netful.tif.
    Intermediates are kept for debugging and verification.
    """
    if passes < 0:
        raise ValueError("order_reduction_passes must be >= 0")
    if passes == 0:
        return

    if not flovec_path.exists():
        raise FileNotFoundError(f"Flow vector file does not exist: {flovec_path}")
    if not netful_path.exists():
        raise FileNotFoundError(f"Stream network file does not exist: {netful_path}")

    wbt = WhiteboxTools(verbose=False, raise_on_error=True)
    wbt.set_working_dir(str(netful_path.parent))

    strahler_path = netful_path.with_name("netful.strahler.tif")
    if strahler_path.exists():
        strahler_path.unlink()

    ret = wbt.strahler_stream_order(
        d8_pntr=str(flovec_path),
        streams=str(netful_path),
        output=str(strahler_path),
        esri_pntr=False,
        zero_background=False,
    )
    if ret != 0 or not strahler_path.exists():
        raise RuntimeError(
            "StrahlerStreamOrder failed "
            f"(flovec={flovec_path}, streams={netful_path}, output={strahler_path})"
        )

    current = strahler_path
    for idx in range(passes):
        is_final = idx == passes - 1
        output = (
            netful_path.with_name(f"netful.pruned_{idx + 1}.tif")
            if is_final
            else netful_path.with_name(f"netful.strahler_pruned_{idx + 1}.tif")
        )
        if output.exists():
            output.unlink()
        ret = wbt.prune_strahler_stream_order(
            streams=str(current),
            output=str(output),
            binary_output=is_final,
        )
        if ret != 0:
            raise RuntimeError(
                "PruneStrahlerStreamOrder failed "
                f"(pass {idx + 1}, input={current}, output={output})"
            )
        LOGGER.info(
            "pruned stream order pass %d: %s -> %s",
            idx + 1,
            current.name,
            output.name,
        )
        # Keep intermediate files for debugging - only advance current pointer
        current = output

    if overwrite_netful and current != netful_path:
        shutil.copy2(current, netful_path)


__all__ = ["_prune_stream_order"]
