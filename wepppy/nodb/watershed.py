from typing import Generator, Dict, Union, Tuple

import os
import json

from os.path import join as _join
from os.path import exists as _exists

import jsonpickle

import wepppy
from wepppy.watershed_abstraction import (
    HillSummary,
    ChannelSummary,
    WatershedAbstraction,
    WeppTopTranslator
)

from .base import NoDbBase, TriggerEvents


class WatershedNoDbLockedException(Exception):
    pass


class Watershed(NoDbBase):
    __name__ = 'Watershed'

    def __init__(self, wd, cfg_fn):
        super(Watershed, self).__init__(wd, cfg_fn)

        self.lock()

        # noinspection PyBroadException
        try:
            self._subs_summary = None
            self._fps_summary = None
            self._structure = None
            self._chns_summary = None
            self._totalarea = None
            self._impoundment_n = 0
            self._centroid = None
            self._outlet_top_id = None

            wat_dir = self.wat_dir
            if not _exists(wat_dir):
                os.mkdir(wat_dir)

            self.dump_and_unlock()

        except Exception:
            self.unlock('-f')
            raise
    #
    # Required for NoDbBase Subclass
    #

    # noinspection PyPep8Naming
    @staticmethod
    def getInstance(wd):
        with open(_join(wd, 'watershed.nodb')) as fp:
            db = jsonpickle.decode(fp.read())
            assert isinstance(db, Watershed)

            if os.path.abspath(wd) != os.path.abspath(db.wd):
                db.wd = wd
                db.lock()
                db.dump_and_unlock()

            return db

    @property
    def _nodb(self):
        return _join(self.wd, 'watershed.nodb')

    @property
    def _lock(self):
        return _join(self.wd, 'watershed.nodb.lock')

    @property
    def sub_n(self) -> int:
        if self._subs_summary is None:
            return 0

        return len(self._subs_summary)

    @property
    def impoundment_n(self) -> int:
        return self._impoundment_n
        
    @property
    def chn_n(self) -> int:
        if self._chns_summary is None:
            return 0

        return len(self._chns_summary)

    @property
    def totalarea(self) -> float:
        return self._totalarea

    @property
    def structure(self):
        return self._structure
        
    @property
    def outlet_top_id(self):
        return self._outlet_top_id
        
    def translator_factory(self):
        if self._chns_summary is None:
            raise Exception('No chn_ids available for translator')
            
        if self._subs_summary is None:
            raise Exception('No sub_ids available for translator')
    
        return WeppTopTranslator(map(int, self._subs_summary.keys()), 
                                 map(int, self._chns_summary.keys()))

    #
    # abstract watershed
    #
    def abstract_watershed(self):
        self.lock()

        # noinspection PyBroadException
        try:
            wat_dir = self.wat_dir
            assert _exists(wat_dir)

            topaz_wd = self.topaz_wd
            assert _exists(topaz_wd)

            _abs = WatershedAbstraction(topaz_wd, wat_dir)
            _abs.abstract()
            _abs.write_slps()
            
            chns_summary = {}
            for k, v in _abs.watershed['channels'].items():
                topaz_id = int(k.replace('chn_', ''))
                chns_summary[topaz_id] = v

            subs_summary = {}
            fps_summary = {}
            for k, v in _abs.watershed['hillslopes'].items():
                topaz_id = int(k.replace('hill_', ''))
                subs_summary[topaz_id] = v
                fps_summary[topaz_id] = _abs.watershed['flowpaths'][k]
                
            self._subs_summary = subs_summary
            self._chns_summary = chns_summary
            self._fps_summary = fps_summary
            self._totalarea = _abs.totalarea
            self._centroid = _abs.centroid.lnglat
            self._outlet_top_id = str(_abs.outlet_top_id)
            self._structure = _abs.structure
            
            del _abs

            self.dump_and_unlock()

            ron = wepppy.Ron.getInstance(self.wd)
            if any(['lt' in ron.mods]):
                wepp = wepppy.nodb.Wepp.getInstance(self.wd)
                wepp.trigger(TriggerEvents.PREPPING_PHOSPHORUS)

        except Exception:
            self.unlock('-f')
            raise

    @property
    def report(self):
        return dict(hillslope_n=self.sub_n,
                    channel_n=self.chn_n,
                    totalarea=self.totalarea)

    @property
    def centroid(self) -> Tuple[float, float]:
        return self._centroid
        
    def sub_summary(self, topaz_id) -> Dict:
        if self._subs_summary is None:
            return None
            
        if str(topaz_id) in self._subs_summary:
            return self._subs_summary[str(topaz_id)].as_dict()
        else:
            return None

    def fps_summary(self, topaz_id):
        if self._fps_summary is None:
            return None

        if topaz_id in self._fps_summary:
            return self._fps_summary[topaz_id]
        else:
            return None

    # gotcha: using __getitem__ breaks jinja's attribute lookup, so...
    def _(self, wepp_id) -> Union[HillSummary, ChannelSummary]:
        translator = self.translator_factory()
        topaz_id = str(translator.top(wepp=int(wepp_id)))
        
        if topaz_id in self._subs_summary:
            return self._subs_summary[topaz_id]
        elif topaz_id in self._chns_summary:
            return self._chns_summary[topaz_id]
            
        raise IndexError
        
    @property
    def subs_summary(self) -> Dict[str, Dict]:
        return {k: v.as_dict() for k, v in self._subs_summary.items()}

    def sub_iter(self) -> Generator[HillSummary, None, None]:
        if self.sub_n > 0:
            for topaz_id, v in self._subs_summary.items():
                yield topaz_id, v
                
    def chn_summary(self, topaz_id) -> Generator[ChannelSummary, None, None]:
        if str(topaz_id) in self._chns_summary:
            return self._chns_summary[str(topaz_id)].as_dict()
        else:
            return None

    @property
    def chns_summary(self) -> Dict[str, Dict]:
        return {k: v.as_dict() for k, v in self._chns_summary.items()}
            
    def chn_iter(self) -> Generator[ChannelSummary, None, None]:
        if self.chn_n > 0:
            for topaz_id, v in self._chns_summary.items():
                yield topaz_id, v
            
    def get_ws(self):
        with open(self.wat_js) as fp:
            return json.load(fp)
