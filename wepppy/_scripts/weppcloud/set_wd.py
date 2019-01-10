import os
from os.path import exists as _exists
from os.path import join as _join

from wepppy.nodb import Climate, Landuse, Ron, Soils, Topaz, Unitizer, Watershed, Wepp, Observed, WeppPost, DebrisFlow
from wepppy.nodb.mods import LakeTahoe, Baer

nodb_d = {
          'climate': Climate,
          'landuse': Landuse,
          'ron': Ron,
          'soils': Soils,
          'topaz': Topaz,
          'unitizer': Unitizer,
          'watershed': Watershed,
          'wepp': Wepp,
          'lt': LakeTahoe,
          'baer': Baer,
          'observed': Observed,
          'wepppost': WeppPost,
          'debris_flow': DebrisFlow
          }

def set_wd(wd):
    assert _exists(wd)

    wd = os.path.abspath(wd)

    for (base, Nodb) in nodb_d.items():
        fn = _join(wd, '%s.nodb' % base)
        if _exists(fn):
            lock = _join(wd, '%s.nodb.lock')
            if _exists(lock):
                os.remove(lock)

            nodb = Nodb.getInstance(wd)
            nodb.lock()
            nodb.wd = wd
            nodb.dump_and_unlock()
            print(fn)


if __name__ == "__main__":
    import sys
    runs = sys.argv[1:]

    for run in runs:
        set_wd(run)

