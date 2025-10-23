"""Debris-flow probability controller.

This module orchestrates debris-flow risk calculations using basin
characteristics (slope, burn severity, soils) and stochastic precipitation
grids. It retrieves precipitation frequency curves from NOAA or the Holden WRF
Atlas, converts durations into hourly intensity, and plugs the results into the
USGS debris-flow empirical equations. Downstream UI dashboards and API clients
consume the predicted debris-flow volume and probability grids.

Inputs:
- Watershed geometry (`Watershed`) for area, ruggedness, and slope metrics.
- Burn severity coverage from `Baer` or `Disturbed` NoDb mods.
- Soil properties (clay content, liquid limit) from the `Soils` controller or
  manual overrides.
- Precipitation frequency data via NOAA Precipitation Frequency Data Server or
  Holden WRF Atlas lookups.

Outputs and integrations:
- In-memory precipitation tables (`self.T`, `self.I`) and debris-flow volume /
  probability matrices keyed by datasource, used by the WEPPcloud run summary.
- Redis task timestamps to notify UI components when the debris-flow analysis
  completes.
"""

from __future__ import annotations

# Copyright (c) 2016-2018, University of Idaho
# All rights reserved.
#
# Roger Lew (rogerlew@gmail.com)
#
# The project described was supported by NSF award number IIA-1301792
# from the NSF Idaho EPSCoR Program and by the National Science Foundation.

import math
import os
from copy import deepcopy
from os.path import exists as _exists
from os.path import join as _join
from typing import ClassVar, Dict, KeysView, List, Optional, TypeAlias

import numpy as np

from wepppy.all_your_base import isfloat
from wepppy.climates import holden_wrf_atlas
from wepppy.climates import noaa_precip_freqs_client
from wepppy.nodb.base import NoDbBase
from wepppy.nodb.core import Ron, Soils, Watershed
from wepppy.nodb.mods.baer import Baer
from wepppy.nodb.mods.disturbed import Disturbed
from wepppy.nodb.redis_prep import RedisPrep, TaskEnum

__all__ = [
    'DebrisFlowNoDbLockedException',
    'DebrisFlow',
]

DurationList: TypeAlias = List[str]
RecurrenceList: TypeAlias = List[float]
FloatMatrix: TypeAlias = List[List[float]]
PrecipTable: TypeAlias = Dict[str, FloatMatrix]
DurationTable: TypeAlias = Dict[str, DurationList]
RecurrenceTable: TypeAlias = Dict[str, RecurrenceList]
ResultTable: TypeAlias = Dict[str, FloatMatrix]


def _duration_in_hours(duration: str) -> float:
    value, unit = duration.split('-')
    quantity = float(value)
    assert unit in ['min', 'hour', 'day']
    if unit == 'min':
        return quantity / 60.0
    if unit == 'day':
        return quantity * 24.0
    return quantity


class DebrisFlowNoDbLockedException(Exception):
    """Raised when the debris-flow controller cannot acquire its NoDb lock."""


class DebrisFlow(NoDbBase):
    """Compute debris-flow volume and probability for the current watershed."""

    __name__: ClassVar[str] = 'DebrisFlow'

    filename: ClassVar[str] = 'debris_flow.nodb'

    def __init__(
        self,
        wd: str,
        cfg_fn: str,
        run_group: Optional[str] = None,
        group_name: Optional[str] = None
    ) -> None:
        super().__init__(wd, cfg_fn, run_group=run_group, group_name=group_name)

        self.I: Optional[PrecipTable] = None
        self.T: Optional[PrecipTable] = None
        self.durations: Optional[DurationTable] = None
        self.rec_intervals: Optional[RecurrenceTable] = None
        self.volume: Optional[ResultTable] = None
        self.prob_occurrence: Optional[ResultTable] = None
        self._datasource: Optional[str] = None

        self.A: Optional[float] = None
        self.B: Optional[float] = None
        self.A_pct: Optional[float] = None
        self.B_pct: Optional[float] = None
        self.C: Optional[float] = None
        self.LL: Optional[float] = None
        self.R: Optional[float] = None
        self.wsarea: Optional[float] = None

        with self.locked():
            self.I = None
            self.T = None
            self.durations = None
            self.rec_intervals = None
            self.volume = None
            self.prob_occurrence = None
            self._datasource = None

            self.A = None
            self.B = None
            self.A_pct = None
            self.B_pct = None
            self.C = None
            self.LL = None
            self.R = None
            self.wsarea = None

    def fetch_precip_data(self) -> None:
        with self.locked():
            self.T = {}
            self.I = {}
            self.durations = {}
            self.rec_intervals = {}

            watershed = Watershed.getInstance(self.wd)
            lng, lat = watershed.centroid
            pf = noaa_precip_freqs_client.fetch_pf(lat=lat, lng=lng)
            if pf is not None:
                _datasource = 'NOAA'

                self.T[_datasource] = (np.array(pf['quantiles']) * 25.4).tolist()
                self.I[_datasource] = (np.array(pf['quantiles']) * 25.4).tolist()
                self.durations[_datasource] = list(pf['durations'])
                self.rec_intervals[_datasource] = list(pf['rec_intervals'])

                for i, d in enumerate(self.durations[_datasource]):
                    hours = _duration_in_hours(d)
                    row = np.array(self.I[_datasource][i])
                    row /= hours
                    self.I[_datasource][i] = row.tolist()

                self._datasource = _datasource

            pf = holden_wrf_atlas.fetch_pf(lat=lat, lng=lng)
            if pf is not None:
                _datasource = 'Holden WRF Atlas'

                precip = np.array(pf['precips'])
                self.T[_datasource] = precip.tolist()
                self.I[_datasource] = precip.copy().tolist()
                self.durations[_datasource] = list(pf['durations'])
                self.rec_intervals[_datasource] = list(pf['rec_intervals'])

                array_T = np.array(self.T[_datasource])
                array_I = np.array(self.I[_datasource])
                shape = (len(self.durations[_datasource]), len(self.rec_intervals[_datasource]))

                array_T.resize(shape)
                array_I.resize(shape)

                for i, d in enumerate(self.durations[_datasource]):
                    hours = _duration_in_hours(d)
                    array_I[i, :] /= hours

                if self._datasource is None:
                    self._datasource = _datasource

                self.I[_datasource] = array_I.tolist()
                self.T[_datasource] = array_T.tolist()

    @property
    def datasource(self) -> str:
        return getattr(self, '_datasource', 'NOAA')

    @property
    def datasources(self) -> Optional[KeysView[str]]:
        if self.I is None:
            return None

        return self.I.keys()

    def run_debris_flow(
        self,
        cc: Optional[float | str] = None,
        ll: Optional[float | str] = None,
        req_datasource: Optional[str] = None
    ) -> None:
        with self.locked():
            wd = self.wd
            soils = Soils.getInstance(wd)
            watershed = Watershed.getInstance(wd)
            ron = Ron.getInstance(wd)

            if 'baer' in ron.mods:
                baer = Baer.getInstance(wd)
            else:
                disturbed = Disturbed.getInstance(wd)

            A = watershed.area_gt30
            A_pct = 100 * A / watershed.wsarea
            A /= 1000 * 1000  # to km^2

            try:
                sbs_coverage = baer.sbs_coverage
            except:
                sbs_coverage = disturbed.sbs_coverage

            B = sbs_coverage['moderate'] * watershed.wsarea + \
                sbs_coverage['high'] * watershed.wsarea
            B_pct = 100 * B / watershed.wsarea
            B /= 1000 * 1000  # to km^2

            if cc is not None:
                assert isfloat(cc)
                cc = float(cc)
                assert cc >= 0.0
                assert cc <= 100.0
                C = cc
            else:
                C = getattr(soils, "clay_pct", None)

            if not isfloat(C):
                C = 7.0

            if ll is not None:
                assert isfloat(ll)
                ll = float(ll)
                assert ll >= 0.0
                assert ll <= 100.0
                LL = ll
            else:
                LL = getattr(soils, "liquid_limit", None)

            if not isfloat(LL):
                LL = 13.25

            R = watershed.ruggedness

            self.A = A
            self.B = B
            self.A_pct = A_pct
            self.B_pct = B_pct
            self.C = C
            self.LL = LL
            self.R = R
            self.wsarea = watershed.wsarea

        self.fetch_precip_data()

        if self.T is None or self.I is None:
            raise DebrisFlowNoDbLockedException("No precipitation data found. Please run fetch_precip_data() first.")

        with self.locked():
            self.volume = {}
            self.prob_occurrence = {}

            for _datasource in self.T:

                T = np.array(self.T[_datasource])
                I = np.array(self.I[_datasource])

                # where
                # A (in km2) is the area of the basin having slopes greater than or equal to 30%,
                # B (in km2) is the area of the basin burned at high and moderate severity,
                # T (in mm) is the total storm rainfall, and 0.3 is a bias correction that changes
                # the predicted estimate from a median to a mean value (Helsel and Hirsch, 2002).
                v = np.exp(7.2 + 0.6 * math.log(A) + 0.7 * B ** 0.5 + 0.2 * T ** 0.5 + 0.3)

                # where
                # %A is the percentage of the basin area with gradients greater than or equal to 30%,
                # R is basin ruggedness,
                # %B is the percentage of the basin area burned at high and moderate severity,
                # I is average storm rainfall intensity (in mm/h),
                # C is clay content (in %),
                # LL is the liquid limit
                x = -0.7 + 0.03 * A_pct - 1.6 * R + 0.06 * B_pct + 0.07 * I + 0.2 * C - 0.4 * LL
                prob_occurrence = np.exp(x) / (1.0 + np.exp(x))

                self.volume[_datasource] = deepcopy(v.tolist())
                self.prob_occurrence[_datasource] = deepcopy(prob_occurrence.tolist())

            if req_datasource is not None and self.volume is not None:
                assert req_datasource in self.volume
                self._datasource = req_datasource

        try:
            prep = RedisPrep.getInstance(self.wd)
            prep.timestamp(TaskEnum.run_debris)
        except FileNotFoundError:
            pass
