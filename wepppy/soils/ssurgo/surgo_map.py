# Copyright (c) 2016-2018, University of Idaho
# All rights reserved.
#
# Roger Lew (rogerlew@gmail.com)
#
from __future__ import annotations

"""Raster helpers for SSURGO/STATSGO mapunit (mukey) rasters."""

# Copyright (c) 2016-2018, University of Idaho
# All rights reserved.
#
# Roger Lew (rogerlew@gmail.com)
#
# The project described was supported by NSF award number IIA-1301792
# from the NSF Idaho EPSCoR Program and by the National Science Foundation.

from collections import Counter
from pathlib import Path
from typing import Iterable, Optional, Tuple, Union

import numpy as np

from wepppy.all_your_base.geo import read_raster

__version__ = "v.0.1.0"


class NoValidSoilsException(Exception):
    """Raised when no valid SSURGO soils can be found within the AOI."""

    __name__ = "No Valid Soils Exception"


class SurgoMap:
    """Small helper around a mukey raster used by `SurgoSoilCollection`."""

    def __init__(self, fname: Union[str, Path]) -> None:
        fname = Path(fname)
        if not fname.exists():
            raise FileNotFoundError(fname)

        data, transform, proj = read_raster(str(fname), dtype=np.int32)

        self.data = data
        self.transform = transform
        self.proj = proj
        self.mukeys = list(set(self.data.flatten()))
        self.fname = str(fname)

    def _get_dominant(
        self,
        indices: Optional[Tuple[np.ndarray, np.ndarray]] = None,
        valid_mukeys: Optional[Iterable[int]] = None,
    ) -> Optional[int]:
        """Return the dominant mukey globally or for the supplied pixel indices."""

        if indices is None:
            subset = self.data

        else:
            subset = self.data[indices]

        flattened = list(subset.flatten())

        sorted_keys = Counter(flattened).most_common()[0]

        if valid_mukeys is None:
            return sorted_keys[0]
        else:  # not strictly necessary but makes the type checking happy
            for key in sorted_keys:
                if key in valid_mukeys:
                    return key

        return None
