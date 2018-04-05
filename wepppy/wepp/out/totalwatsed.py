from collections import OrderedDict
import csv

import numpy as np

from wepppy.all_your_base import determine_wateryear

class TotalWatSed(object):

    hdr = ['Julian', 'Year', 'Area (m^2)', 'Precip Vol (m^3)', 'Rain + Melt Vol (m^3)',
           'Transpiration Vol (m^3)', 'Evaporation Vol (m^3)', 'Percolation Vol (m^3)',
           'Runoff Vol (m^3)', 'Lateral Flow Vol (m^3)', 'Storage Vol (m^3)', 'Sed. Det. (kg)',
           'Sed. Dep. (kg)', 'Sed. Del (kg)',
           'Class 1', 'Class 2', 'Class 3', 'Class 4', 'Class 5']

    types = [int, int, float, float, float, float, float, float, float, float,
             float, float, float, float, float, float, float, float, float]

    def __init__(self, fn,
                 baseflowOpts,
                 phosOpts=None):

        from wepppy.nodb import PhosphorusOpts, BaseflowOpts
        hdr = self.hdr
        types = self.types

        # read the loss report
        with open(fn) as fp:
            lines = fp.readlines()

        d = OrderedDict((k, []) for k in hdr)

        for L in lines:
            L = L.split()
            assert len(L) == len(hdr)
            assert len(L) == len(types)

            for k, v, _type in zip(hdr, L, types):
                d[k].append(_type(v))

        for k in d:
            d[k] = np.array(d[k])

        d['Area (ha)'] = d['Area (m^2)'] / 10000.0
        d['Cummulative Sed. Del (tonnes)'] = np.cumsum(d['Sed. Del (kg)'] / 1000.0)
        d['Sed. Del Density (tonne/ha)'] = (d['Sed. Del (kg)'] / 1000.0) / d['Area (ha)']
        d['Precip (mm)'] = d['Precip Vol (m^3)'] / d['Area (m^2)'] * 1000.0
        d['Rain + Melt (mm)'] = d['Rain + Melt Vol (m^3)'] / d['Area (m^2)'] * 1000.0
        d['Transpiration (mm)'] = d['Transpiration Vol (m^3)'] / d['Area (m^2)'] * 1000.0
        d['Evaporation (mm)'] = d['Evaporation Vol (m^3)'] / d['Area (m^2)'] * 1000.0
        d['ET (mm)'] = d['Evaporation (mm)'] + d['Transpiration (mm)']
        d['Percolation (mm)'] = d['Percolation Vol (m^3)'] / d['Area (m^2)'] * 1000.0
        d['Runoff (mm)'] = d['Runoff Vol (m^3)'] / d['Area (m^2)'] * 1000.0
        d['Lateral Flow (mm)'] = d['Lateral Flow Vol (m^3)'] / d['Area (m^2)'] * 1000.0
        d['Storage (mm)'] = d['Storage Vol (m^3)'] / d['Area (m^2)'] * 1000.0

        # calculate Res volume, baseflow, and aquifer losses
        d['Reservoir Volume (mm)'] = [baseflowOpts.gwstorage]
        d['Baseflow (mm)'] = [0.0]
        d['Aquifer Losses (mm)'] = []

        for perc in d['Percolation (mm)']:
            d['Aquifer Losses (mm)'].append(d['Reservoir Volume (mm)'][-1] * baseflowOpts.dscoeff)
            d['Reservoir Volume (mm)'].append(d['Reservoir Volume (mm)'][-1] -
                                              d['Baseflow (mm)'][-1] +
                                              d['Percolation (mm)'][-1] +
                                              d['Aquifer Losses (mm)'][-1])
            d['Baseflow (mm)'].append(d['Reservoir Volume (mm)'][-1] * baseflowOpts.bfcoeff)

        d['Reservoir Volume (mm)'] = np.array(d['Reservoir Volume (mm)'][1:])
        d['Baseflow (mm)'] = np.array(d['Baseflow (mm)'][1:])
        d['Aquifer Losses (mm)'] = np.array(d['Aquifer Losses (mm)'])

        d['Streamflow (mm)'] = d['Runoff (mm)'] + d['Lateral Flow (mm)'] + d['Baseflow (mm)']

        d['Simulated SWE (mm)'] = [0.0]
        for p, rm in zip(d['Precip (mm)'], d['Rain + Melt (mm)']):
            d['Simulated SWE (mm)'].append(p - rm + d['Simulated SWE (mm)'][-1])
        d['Simulated SWE (mm)'] = np.array(d['Simulated SWE (mm)'][1:])

        d['Simulated Sed. Del (tonne/day)'] = d['Sed. Del (kg)'] / 1000.0

        if phosOpts is not None:
            assert isinstance(phosOpts, PhosphorusOpts)
            if phosOpts.isvalid:
                d['Simulated P Load (mg)'] = d['Sed. Del (kg)'] * phosOpts.sediment
                d['Simulated P Runoff (mg)'] = d['Runoff (mm)'] * phosOpts.surf_runoff * d['Area (ha)']
                d['Simulated P Lateral (mg)'] = d['Lateral Flow (mm)'] * phosOpts.lateral_flow * d['Area (ha)']
                d['Simulated P Baseflow (mg)'] = d['Baseflow (mm)'] * phosOpts.baseflow * d['Area (ha)']
                d['Simulated Total P (kg)'] = (d['Simulated P Load (mg)'] +
                                               d['Simulated P Runoff (mg)'] +
                                               d['Simulated P Lateral (mg)'] +
                                               d['Simulated P Baseflow (mg)']) / 1000.0 / 1000.0
                d['Simulated Particulate P (kg)'] = d['Simulated P Load (mg)'] / 1000000.0
                d['Simulated Soluble Reactive P (kg)'] = d['Simulated Total P (kg)'] - d['Simulated Particulate P (kg)']

                d['Simulated P Total (kg/ha)'] = d['Simulated Total P (kg)'] / d['Area (ha)']
                d['Simulated Particulate P (kg/ha)'] = d['Simulated Particulate P (kg)'] / d['Area (ha)']
                d['Simulated Soluble Reactive P (kg/ha)'] = d['Simulated Soluble Reactive P (kg)'] / d['Area (ha)']

        d['Water Year'] = []
        for j, y in zip(d['Julian'], d['Year']):
            d['Water Year'].append(determine_wateryear(y, j=j))

        for k in d:
            d[k] = [float(v) for v in d[k]]

        self.d = d

    def export(self, fn):
        d = self.d
        with open(fn, 'w') as fp:
            wtr = csv.DictWriter(fp,
                                 fieldnames=list(d.keys()),
                                 lineterminator='\n')
            wtr.writeheader()
            for i, yr in enumerate(d['Year']):
                wtr.writerow(OrderedDict([(k, d[k][i]) for k in d]))

if __name__ == "__main__":
    from pprint import pprint
    fn = '/geodata/weppcloud_runs/ef264d6f-5449-4c6d-bce9-f6d4e5938be3/wepp/output/totalwatsed.txt'
    from wepppy.nodb import PhosphorusOpts, BaseflowOpts
    phosOpts = PhosphorusOpts()
    phosOpts.surf_runoff = 0.0118
    phosOpts.lateral_flow = 0.0118
    phosOpts.baseflow = 0.0196
    phosOpts.sediment = 1024
    baseflowOpts = BaseflowOpts()
    totwatsed = TotalWatSed(fn, baseflowOpts, phosOpts=phosOpts)
    totwatsed.export('/home/weppdev/totwatsed.csv')