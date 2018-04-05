# Copyright (c) 2016-2018, University of Idaho
# All rights reserved.
#
# Roger Lew (rogerlew.gmail.com)
#
# The project described was supported by NSF award number IIA-1301792
# from the NSF Idaho EPSCoR Program and by the National Science Foundation.

import time
import io
import pandas as pd

from wepppy.all_your_base import *


def retrieve_historical_timeseries(lon, lat, start_year, end_year):
    assert isint(start_year)
    assert isint(end_year)
    
    start_year = int(start_year)
    end_year = int(end_year)
    
    years = ','.join(str(v) for v in range(start_year, end_year+1))
    
    assert start_year <= end_year
    assert 1980 <= start_year <= int(time.strftime("%Y"))-1
    assert 1980 <= end_year <= int(time.strftime("%Y"))-1
    
    # request data
    url = 'https://daymet.ornl.gov/data/send/saveData'\
          '?lat={lat}&lon={lon}'\
          '&measuredParams=tmax,tmin,dayl,prcp,srad,swe,vp'\
          '&year={years}'\
          .format(lat=lat, lon=lon, years=years)
          
    r = requests.get(url)
    
    # create a virtual file to create pandas dataframe
    fp = io.StringIO()
    fp.write(r.text)
    fp.seek(0)
    
    # create dataframe
    df = pd.read_csv(fp, header=6)
    df.index = pd.to_datetime(df.year.astype(str) + '-' + 
                              df.yday.astype(str), format="%Y-%j")
    df.columns = [c.replace(' ', '') for c in df.columns]
    
    # return dataframe
    return df


if __name__ == "__main__":
    df2 = retrieve_historical_timeseries(-116, 47, 2015, 2016)
    print(len(df2.index))
