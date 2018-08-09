# Copyright (c) 2016-2018, University of Idaho
# All rights reserved.
#
# Roger Lew (rogerlew.gmail.com)
#
# The project described was supported by NSF award number IIA-1301792
# from the NSF Idaho EPSCoR Program and by the National Science Foundation.

from collections import OrderedDict
from copy import deepcopy

from wepppy.all_your_base import find_ranges

unit_consistency_map = {
    'T/ha/yr': 'tonne/ha/yr',
    'tonnes/ha': 'tonne/ha',
    'tonnes/yr': 'tonne/yr',
    None: ''
}


def _find_tbl_starts(section_index, lines):
    """
    next three tables are the hill, channel, outlet
    find the table header lines

    :param section_index: integer starting index of section e.g.
                          "ANNUAL SUMMARY FOR WATERSHED IN YEAR"
    :param lines: loss_pw0.txt as a list of strings
    :return: hill0, chn0, out0
        index to line starting the hill, channel, and outlet table
    """
    header_indx = []

    for i, L in enumerate(lines[section_index + 2:]):
        if L.startswith('----'):
            header_indx.append(i)

    hill0 = header_indx[0] + 1 + section_index + 2
    chn0 = header_indx[1] + 2 + section_index + 2  # channel and outlet summary
    out0 = header_indx[2] + 2 + section_index + 2  # have a blank line before the data

    return hill0, chn0, out0


def _parse_tbl(lines, hdr):
    data = []
    for L in lines:
        if len(L) == 0:
            return data

        row = []

        for v in L.split():
            if v.count('.') == 2:

                indx = v.find('.')
                tok0 = v[:indx + 3]
                tok1 = v[indx + 3:]

                row.append(float(tok0))
                row.append(float(tok1))

            elif '.' in v:
                row.append(float(v))
            else:
                # noinspection PyBroadException
                try:
                    row.append(int(v))
                except Exception:
                    row.append(v)

        assert len(hdr) == len(row), (hdr, row, lines[0])
        data.append(OrderedDict(zip(hdr, row)))

    return data


def _parse_out(lines):
    data = []
    for L in lines:
        if len(L) == 0:
            return data

        assert '=' in L
        key, v = L.split('=')
        v = v.split()

        if len(v) == 2:
            v, units = v
            units = units.strip()
            units = unit_consistency_map.get(units, units)

        else:
            v = v[0]
            units = None

        key = key.strip()

        if '.' in v:
            v = float(v)
        else:
            # noinspection PyBroadException
            try:
                v = int(v)
            except Exception:
                v = v.strip()

        data.append(dict(key=key, v=v, units=units))

    return data


class Loss(object):
    hill_hdr = (
        'Type',
        'Hillslopes',
        'Runoff Volume',
        'Subrunoff Volume',
        'Baseflow Volume',
        'Soil Loss',
        'Sediment Deposition',
        'Sediment Yield',
        'Solub. React. Phosphorus',
        'Particulate Phosphorus',
        'Total Phosphorus'
    )

    hill_units = (
        None, None, 'm^3', 'm^3', 'm^3', 'kg', 'kg', 'kg', 'kg', 'kg', 'kg'
    )

    hill_avg_hdr = (
        'Type',
        'Hillslopes',
        'Runoff Volume',
        'Subrunoff Volume',
        'Baseflow Volume',
        'Soil Loss',
        'Sediment Deposition',
        'Sediment Yield',
        'Hillslope Area',
        'Solub. React. Phosphorus',
        'Particulate Phosphorus',
        'Total Phosphorus'
    )

    hill_avg_units = (
        None, None, 'm^3', 'm^3', 'm^3', 'kg', 'kg', 'kg', 'ha', 'kg', 'kg', 'kg'
    )

    chn_hdr = (
        'Type',
        'Channels and Impoundments',
        'Discharge Volume',
        'Sediment Yield',
        'Soil Loss',
        'Upland Charge',
        'Subsuface Flow Volume',
        'Solub. React. Phosphorus',
        'Particulate Phosphorus',
        'Total Phosphorus'
    )

    chn_units = (
        None, None, 'm^3', 'tonne', 'kg', 'm^3', 'm^3', 'kg', 'kg', 'kg', 'kg'
    )

    chn_avg_hdr = (
        'Type',
        'Channels and Impoundments',
        'Discharge Volume',
        'Sediment Yield',
        'Soil Loss',
        'Upland Charge',
        'Subsuface Flow Volume',
        'Contributing Area',
        'Solub. React. Phosphorus',
        'Particulate Phosphorus',
        'Total Phosphorus'
    )

    chn_avg_units = (
        None, None, 'm^3', 'tonne', 'kg', 'm^3', 'm^3', 'kg', 'ha', 'kg', 'kg', 'kg'
    )

    def __init__(self, fn, wd=None, exclude_yr_indxs=[0, 1, 2]):
        hill_hdr = self.hill_hdr
        hill_avg_hdr = self.hill_avg_hdr
        chn_hdr = self.chn_hdr
        chn_avg_hdr = self.chn_avg_hdr

        # read the loss report
        with open(fn) as fp:
            lines = fp.readlines()

        # strip trailing and leading white space
        lines = [L.strip() for L in lines]

        # find year indexes

        yr_indxs = []
        avg_indx = None
        for i, L in enumerate(lines):
            if 'ANNUAL SUMMARY FOR WATERSHED IN YEAR' in L:
                yr = int(''.join(c for c in L if c in '0123456789'))
                yr_indxs.append((i, yr))

            if 'YEAR AVERAGE ANNUAL VALUES FOR WATERSHED' in L:
                avg_indx = i

        num_years = len(yr_indxs)
        assert avg_indx is not None
        assert num_years > 0

        years = [yr for i, yr in yr_indxs]

        yearlies = {}
        for yr_indx, yr in yr_indxs:
            hill0, chn0, out0 = _find_tbl_starts(yr_indx, lines)
            hill_tbl = _parse_tbl(lines[hill0:], hill_hdr)
            chn_tbl = _parse_tbl(lines[chn0:], chn_hdr)
            out_tbl = _parse_out(lines[out0:])
            yearlies[yr] = dict(hill_tbl=deepcopy(hill_tbl),
                                chn_tbl=deepcopy(chn_tbl),
                                out_tbl=deepcopy(out_tbl))

        hill0, chn0, out0 = _find_tbl_starts(avg_indx, lines)
        hill_tbl = _parse_tbl(lines[hill0:], hill_avg_hdr)
        chn_tbl = _parse_tbl(lines[chn0:], chn_avg_hdr)
        out_tbl = _parse_out(lines[out0:])

        # remove the years from average
        if exclude_yr_indxs is not None and num_years > len(exclude_yr_indxs):

            # average out years for outlet table
            _out_tbl = deepcopy(out_tbl)
            for j, d in enumerate(_out_tbl):
                if _out_tbl[j]['key'] == 'Total contributing area to outlet':
                    continue
                    
                _out_tbl[j]['v'] = 0

            avg_years = []
            for i, yr in enumerate(years):
                if i in exclude_yr_indxs:
                    continue

                for j, d in enumerate(yearlies[yr]['out_tbl']):
                    if _out_tbl[j]['key'] == 'Total contributing area to outlet':
                        continue

                    _out_tbl[j]['v'] += yearlies[yr]['out_tbl'][j]['v']

                avg_years.append(yr)

            for j, d in enumerate(_out_tbl):
                if _out_tbl[j]['key'] == 'Total contributing area to outlet':
                    continue

                _out_tbl[j]['v'] /= float(len(avg_years))

            out_tbl = _out_tbl

            # average out years for hill table
            _hill_tbl = deepcopy(hill_tbl)
            for j, d in enumerate(hill_tbl):
                for var in hill_hdr[2:]:
                    hill_tbl[j][var] = 0

            avg_years = []
            for i, yr in enumerate(years):
                if i in exclude_yr_indxs:
                    continue

                for j, d in enumerate(hill_tbl):
                    for var in hill_hdr[2:]:
                        _hill_tbl[j][var] += yearlies[yr]['hill_tbl'][j][var]

                avg_years.append(yr)

            for var in hill_hdr[2:]:
                _hill_tbl[j][var] /= float(len(avg_years))

            hill_tbl = _hill_tbl

            # average out years for chn table
            _chn_tbl = deepcopy(chn_tbl)
            for j, d in enumerate(chn_tbl):
                for var in chn_hdr[2:]:
                    chn_tbl[j][var] = 0

            avg_years = []
            for i, yr in enumerate(years):
                if i in exclude_yr_indxs:
                    continue

                for j, d in enumerate(chn_tbl):
                    for var in chn_hdr[2:]:
                        _chn_tbl[j][var] += yearlies[yr]['chn_tbl'][j][var]

                avg_years.append(yr)

            for var in chn_hdr[2:]:
                _chn_tbl[j][var] /= float(len(avg_years))

            chn_tbl = _chn_tbl


        if wd is not None:
            import wepppy

            landuse = wepppy.nodb.Landuse.getInstance(wd)
            soils = wepppy.nodb.Soils.getInstance(wd)
            watershed = wepppy.nodb.Watershed.getInstance(wd)
            translator = watershed.translator_factory()

            for i in range(len(hill_tbl)):
                row = hill_tbl[i]
                wepp_id = row['Hillslopes']

                topaz_id = translator.top(wepp=wepp_id)
                sub_summary = watershed.sub_summary(str(topaz_id))
                area = row['Hillslope Area']
                hill_tbl[i]['WeppID'] = wepp_id
                hill_tbl[i]['TopazID'] = topaz_id
                hill_tbl[i]['Landuse'] = landuse.domlc_d[str(topaz_id)]
                hill_tbl[i]['Soil'] = soils.domsoil_d[str(topaz_id)]
                hill_tbl[i]['Length'] = sub_summary['length']
                hill_tbl[i]['Runoff'] = row['Runoff Volume'] / (area * 1000.0)
                hill_tbl[i]['Subrunoff'] = row['Subrunoff Volume'] / (area * 1000.0)
                hill_tbl[i]['Baseflow'] = row['Baseflow Volume'] / (area * 1000.0)

                _loss = row['Soil Loss'] / area
                _dep = row['Sediment Deposition'] / area
                _yield = row['Sediment Yield'] / area
                hill_tbl[i]['Soil Loss Density'] = _loss
                hill_tbl[i]['Sediment Deposition Density'] = _dep
                hill_tbl[i]['Sediment Yield Density'] = _yield
                hill_tbl[i]['DepLoss'] = _yield - _dep

                if 'Solub. React. Phosphorus' in row:
                    hill_tbl[i]['Solub. React. P Density'] = row['Solub. React. Phosphorus'] / area

                if 'Particulate Phosphorus' in row:
                    hill_tbl[i]['Particulate P Density'] = row['Particulate Phosphorus'] / area

                if 'Total Phosphorus' in row:
                    hill_tbl[i]['Total P Density'] = row['Total Phosphorus'] / area

            for i in range(len(chn_tbl)):
                row = chn_tbl[i]
                wepp_id = row['Channels and Impoundments']

                topaz_id = translator.top(chn_enum=wepp_id)
                chn_summary = watershed.chn_summary(str(topaz_id))
                area = chn_summary['area'] / 10000.0
                chn_tbl[i]['WeppID'] = wepp_id
                chn_tbl[i]['TopazID'] = topaz_id
                chn_tbl[i]['Area'] = area
                chn_tbl[i]['Length'] = chn_summary['length']
                chn_tbl[i]['Sediment Yield Density'] = row['Sediment Yield'] / area
                chn_tbl[i]['Soil Loss Density'] = row['Soil Loss'] / area

                if 'Solub. React. Phosphorus' in row:
                    chn_tbl[i]['Solub. React. P Density'] = row['Solub. React. Phosphorus'] / area

                if 'Particulate Phosphorus' in row:
                    chn_tbl[i]['Particulate P Density'] = row['Particulate Phosphorus'] / area

                if 'Total Phosphorus' in row:
                    chn_tbl[i]['Total P Density'] = row['Total Phosphorus'] / area

        self.hill_tbl = hill_tbl
        self.chn_tbl = chn_tbl
        self.out_tbl = out_tbl
        self.wsarea = [d['v'] for d in out_tbl if d['key'] == 'Total contributing area to outlet'][0]
        self.yearlies = yearlies
        self.years = years
        self.num_years = num_years
        self.avg_years = avg_years

    @property
    def avg_annual_years(self):
        return find_ranges(self.avg_years,
                           as_str=True)

    @property
    def excluded_years(self):
        return find_ranges(sorted([yr for yr in self.years if yr not in self.avg_years]),
                           as_str=True)

    def __str__(self):
        return "Loss(hill_tbl={0.hill_tbl}, chn_tbl={0.chn_tbl}, out_tbl={0.out_tbl}, wsarea={0.wsarea}, "\
               "yearlies={0.yearlies}, years={0.years}, num_years={0.num_years}, avg_years={0.avg_years})".format(self)


if __name__ == "__main__":
    loss = Loss('/geodata/weppcloud_runs/88d80fb4-41b5-4fb7-a9aa-5e2de0892c4f/wepp/output/loss_pw0.txt',
                '/geodata/weppcloud_runs/88d80fb4-41b5-4fb7-a9aa-5e2de0892c4f/')

    #print(loss.excluded_years)

    from wepppy.wepp.stats import (
        OutletSummary,
        HillSummary,
        ChannelSummary,
        TotalWatbal
    )

    chn_rpt = ChannelSummary(loss)

    for row in chn_rpt:
        for k, y in zip(chn_rpt.header, row):
            print(k, y)

#    for d in OutletSummary(loss):
#        print(d)
