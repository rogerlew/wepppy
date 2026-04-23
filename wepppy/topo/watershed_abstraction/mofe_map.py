from __future__ import annotations

import importlib
from functools import lru_cache
from typing import Callable, Mapping, Sequence

import numpy as np


@lru_cache(maxsize=1)
def _load_wepppyo3_mofe_map_assigner() -> Callable[..., np.ndarray]:
    try:
        module = importlib.import_module("wepppyo3.watershed_abstraction")
    except Exception as exc:
        raise RuntimeError(
            "MOFE map assignment requires `wepppyo3.watershed_abstraction`; install/update wepppyo3 to continue."
        ) from exc

    assigner = getattr(module, "assign_mofe_map", None)
    if not callable(assigner):
        raise RuntimeError(
            "MOFE map assignment requires `wepppyo3.watershed_abstraction.assign_mofe_map`."
        )

    return assigner


def assign_mofe_map_with_wepppyo3(
    subwta: np.ndarray,
    discha: np.ndarray,
    topaz_ids: Sequence[int],
    d_fractions_by_topaz: Mapping[int, np.ndarray],
) -> np.ndarray:
    assigner = _load_wepppyo3_mofe_map_assigner()
    payload = {
        int(topaz_id): [float(value) for value in np.asarray(d_fractions, dtype=np.float64)]
        for topaz_id, d_fractions in d_fractions_by_topaz.items()
    }
    result = assigner(
        np.asarray(subwta, dtype=np.int32),
        np.asarray(discha, dtype=np.int32),
        [int(topaz_id) for topaz_id in topaz_ids],
        payload,
    )
    return np.asarray(result, dtype=np.int32)
