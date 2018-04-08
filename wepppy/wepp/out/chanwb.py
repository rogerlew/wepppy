# Copyright (c) 2016-2018, University of Idaho
# All rights reserved.
#
# Roger Lew (rogerlew.gmail.com)
#
# The project described was supported by NSF award number IIA-1301792
# from the NSF Idaho EPSCoR Program and by the National Science Foundation.

from os.path import exists as _exists
from os.path import join as _join

from datetime import datetime, timedelta
from collections import OrderedDict
import numpy as np
from scipy import stats

class Chanwb:
    def __init__(self, fname):
        assert _exists(fname)

        with open(fname) as fp:
            lines = fp.readlines()

        hdr = lines[10].split()

        lines = np.array([[float(v) for v in L.split()] for L in lines[11:]])

        d = { 'Date': [], 'M': [], 'D': [] }
        for i, colname in enumerate(hdr):
            d[colname] = lines[:, i]

        d['Year'] = np.array(d['Year'], dtype=np.int32)
        d['Day'] = np.array(d['Day'], dtype=np.int32)
        d['Elmt_ID'] = np.array(d['Elmt_ID'], dtype=np.int32)
        d['Chan_ID'] = np.array(d['Chan_ID'], dtype=np.int32)

        for year, julday in zip(d['Year'], d['Day']):
            dt = datetime(int(year), 1, 1) + timedelta(int(julday) - 1)
            d['Date'].append(np.datetime64(dt))
            d['M'].append(dt.month)
            d['D'].append(dt.day)

        d['Date'] = np.array(d['Date'])
        d['M'] = np.array(d['M'])
        d['D'] = np.array(d['D'])
        d['Julian'] = d['Day']
        del d['Day']

        self.data = d
        self.hdr = hdr
        self.units = [None, None, None, None, 'm^3', 'm^3', 'm^3', 'm^3', 'm^3', 'm^3']

    def calc_streamflow(self, wsarea):
        return self.data['Outflow'] / wsarea

if __name__ == "__main__":
    chnwat = Chanwb('/geodata/weppcloud_runs/f26c3690-c491-478f-90f9-f6710abb2618/wepp/output/chanwb.out')

    print(chnwat.data.keys())

