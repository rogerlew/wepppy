# Copyright (c) 2016-2018, University of Idaho
# All rights reserved.
#
# Roger Lew (rogerlew@gmail.com)
#
# The project described was supported by NSF award number IIA-1301792
# from the NSF Idaho EPSCoR Program and by the National Science Foundation.


from wepppy.climates.cligen import par_mod


def eobs_mod(par: int, years: int, lng: float, lat: float, wd: str,
              nwds_method='', randseed=None, cliver=None, suffix='', logger=None):

    return par_mod(par=par, years=years, lng=lng, lat=lat, wd=wd, monthly_dataset='eobs',
                   nwds_method=nwds_method, randseed=randseed, cliver=cliver, suffix=suffix,
                   logger=logger)
