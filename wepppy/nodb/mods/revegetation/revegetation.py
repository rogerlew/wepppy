"""Revegetation cover transform controller.

This module manages post-fire revegetation cover transforms that rescale RAP
fractional cover time series before WEPP or RHEM runs. It keeps a working
directory under the run root, validates user-provided CSV transforms, and
loads library scenarios shipped with WEPPcloud.

Inputs:
- Scenario name selected in the UI or `user_cover_transform` for ad-hoc CSVs.
- Cover transform CSVs where column headers pair soil burn severity and
  vegetation class, followed by yearly scale factors.

Outputs and downstream consumers:
- `revegetation/<scenario>.csv` copied into the working directory for job
  reproducibility.
- `cover_transform` property returning per-band scale factors consumed by
  `RAP_TS` when generating WEPP `.cov` files and by RHEM dashboards.
- Flags that indicate whether the active transform was user supplied.
"""

from __future__ import annotations

import os
import shutil
from os.path import exists as _exists
from os.path import join as _join
from typing import ClassVar, Dict, Optional, Tuple, TypeAlias

import numpy as np
import numpy.typing as npt
import pandas as pd

from wepppy.nodb.base import NoDbBase, TriggerEvents, nodb_setter

__all__: list[str] = [
    'RevegetationNoDbLockedException',
    'Revegetation',
]

_THISDIR = os.path.dirname(__file__)
_DATA_DIR = _join(_THISDIR, 'data')
_COVER_TRANSFORMS_DIR = _join(_DATA_DIR, 'cover_transforms')

CoverTransform: TypeAlias = Dict[Tuple[str, str], npt.NDArray[np.float32]]


class RevegetationNoDbLockedException(Exception):
    """Raised when the revegetation NoDb instance cannot acquire its lock."""


class Revegetation(NoDbBase):
    __name__: ClassVar[str] = 'Revegetation'

    filename: ClassVar[str] = 'revegetation.nodb'

    def __init__(
        self,
        wd: str,
        cfg_fn: str,
        run_group: Optional[str] = None,
        group_name: Optional[str] = None
    ) -> None:
        super().__init__(wd, cfg_fn, run_group=run_group, group_name=group_name)

        self._cover_transform_fn: str = ''
        self._user_defined_cover_transform: bool = False

        with self.locked():
            self.clean()
            self._cover_transform_fn = ''
            self._user_defined_cover_transform = False

    def validate_user_defined_cover_transform(self, fn: str) -> None:
        with self.locked():
            assert _exists(_join(self.revegetation_dir, fn)), fn
            self._cover_transform_fn = fn
            self._user_defined_cover_transform = True

    @property
    def user_defined_cover_transform(self) -> bool:
        return self._user_defined_cover_transform

    def load_cover_transform(self, reveg_scenario: str) -> None:
        if reveg_scenario == 'user_cover_transform':
            return

        if reveg_scenario == '':
            self.cover_transform_fn = ''
            return

        src_fn = _join(_COVER_TRANSFORMS_DIR, reveg_scenario)
        assert _exists(src_fn), src_fn
        self.cover_transform_fn = reveg_scenario
        shutil.copyfile(src_fn, self.cover_transform_path)

    @property
    def cover_transform_fn(self) -> str:
        return self._cover_transform_fn

    @cover_transform_fn.setter
    @nodb_setter
    def cover_transform_fn(self, value: str) -> None:
        self._cover_transform_fn = value

    @property
    def revegetation_dir(self) -> str:
        return _join(self.wd, 'revegetation')

    @property
    def cover_transform_path(self) -> str:
        return _join(self.revegetation_dir, self.cover_transform_fn)

    @property
    def cover_transform(self) -> Optional[CoverTransform]:
        cover_transform_path = self.cover_transform_path
        if not _exists(cover_transform_path) or not cover_transform_path.endswith('.csv'):
            return None

        df = pd.read_csv(cover_transform_path, header=None)

        soil_burn_classes = df.iloc[0]
        landuse_labels = df.iloc[1]

        staged: Dict[Tuple[str, str], list[float]] = {}
        for col in range(df.shape[1]):
            key = (str(soil_burn_classes[col]), str(landuse_labels[col]))
            staged.setdefault(key, []).extend(df.iloc[2:, col].tolist())

        cover_transform: CoverTransform = {}
        for key, values in staged.items():
            cover_transform[key] = np.array(values, dtype=np.float32)

        return cover_transform

    def clean(self) -> None:
        revegetation_dir = self.revegetation_dir
        if _exists(revegetation_dir):
            shutil.rmtree(revegetation_dir)
        os.mkdir(revegetation_dir)

    def on(self, evt: TriggerEvents) -> None:
        pass
