# Copyright (c) 2016-2018, University of Idaho
# All rights reserved.
#
# Roger Lew (rogerlew@gmail.com)
#
# The project described was supported by NSF award number IIA-1301792
# from the NSF Idaho EPSCoR Program and by the National Science Foundation.

"""Legacy Prep controller used for timestamp tracking (deprecated)."""

from __future__ import annotations

import time
from typing import Dict, Optional

from deprecated import deprecated

# nonstandard

# weppy submodules
from .base import NoDbBase, nodb_setter

__all__ = [
    'PrepNoDbLockedException',
    'Prep',
]

@deprecated(reason="Superseded by RedisPrep; retained for legacy run replay.")
class PrepNoDbLockedException(Exception):
    """Legacy sentinel raised when Prep locking failed."""


@deprecated(reason="Superseded by RedisPrep; retained for legacy run replay.")
class Prep(NoDbBase):
    """Minimal NoDb controller that tracks SBS state and timestamps."""

    __name__ = 'Prep'

    filename = 'prep.nodb'

    def __init__(
        self,
        wd: str,
        cfg_fn: str,
        run_group: Optional[str] = None,
        group_name: Optional[str] = None,
    ) -> None:

        super().__init__(wd, cfg_fn, run_group=run_group, group_name=group_name)

        with self.locked():
            self._sbs_required = False
            self._has_sbs = False
            self._timestamps: Dict[str, int] = {}

    @property
    def sbs_required(self) -> bool:
        """Flag indicating whether wildfire soil burn severity is required."""

        return getattr(self, '_sbs_required', False)

    @sbs_required.setter
    @nodb_setter
    def sbs_required(self, value: bool) -> None:
        self._sbs_required = value

    @property
    def has_sbs(self) -> bool:
        """Return whether the run currently has SBS data ingested."""

        return getattr(self, '_has_sbs', False)

    @has_sbs.setter
    @nodb_setter
    def has_sbs(self, value: bool) -> None:
        self._has_sbs = value

    def timestamp(self, key: str) -> None:
        """Record the current epoch timestamp for ``key``."""

        now = int(time.time())
        self.__setitem__(key, now)

    def __setitem__(self, key: str, value: int) -> None:
        """Persist a timestamp value under ``key`` within a locked context."""

        with self.locked():
            self._timestamps[key] = value

    def __getitem__(self, key: str) -> Optional[int]:
        """Return the timestamp stored for ``key`` if present."""

        return self._timestamps.get(key)
