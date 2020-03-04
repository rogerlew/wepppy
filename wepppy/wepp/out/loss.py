# Copyright (c) 2016-2018, University of Idaho
# All rights reserved.
#
# Roger Lew (rogerlew@gmail.com)
#
# The project described was supported by NSF award number IIA-1301792
# from the NSF Idaho EPSCoR Program and by the National Science Foundation.

from collections import OrderedDict
from copy import deepcopy

from wepppy.all_your_base import find_ranges, isfloat

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

                if '*' in v:
                    if v.endswith('*'):
                        # cases like '1204.543********'
                        row.append(float(v.replace('*', '')))
                        row.append('********')
                    else:
                        # haven't seen this, flat-files... ugh.
                        row.append('********')
                        row.append(float(v.replace('*', '')))
                else:
                    row.append(float(v))

            else:
                # noinspection PyBroadException
                try:
                    # catches the '********' case
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

    def __init__(self, fn, has_phosphorus, wd=None, exclude_yr_indxs=None):
        hill_hdr = self.hill_hdr
        hill_avg_hdr = self.hill_avg_hdr
        chn_hdr = self.chn_hdr
        chn_avg_hdr = self.chn_avg_hdr
        avg_years = None

        # read the loss report
        with open(fn) as fp:
            lines = fp.readlines()

        lines = [L.replace('*** total soil loss < 1 kg ***', '') for L in lines]

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

        # Find class table
        indx0 = []
        for i, L in enumerate(lines):
            if 'sediment particle information leaving' in L.lower():
                indx0.append(i)

        if len(indx0) == 0:
            class_data = None
        else:
            indx0 = indx0[-1]
            lines = lines[indx0:]

            assert lines[7].startswith('1')
            assert lines[8].startswith('2')
            assert lines[9].startswith('3')
            assert lines[10].startswith('4')
            assert lines[11].startswith('5')

            class_data = _parse_tbl(lines[7:12],
                                    ['Class', 'Diameter', 'Specific Gravity',
                                     'Pct Sand', 'Pct Silt', 'Pct Clay', 'Pct OM',
                                     'Fraction In Flow Exiting'])

        # remove the years from average
        assert exclude_yr_indxs is None

        # if exclude_yr_indxs is not None and num_years > len(exclude_yr_indxs):
        #
        #     # average out years for outlet table
        #     _out_tbl = deepcopy(out_tbl)
        #     for j, d in enumerate(_out_tbl):
        #         if _out_tbl[j]['key'] == 'Total contributing area to outlet':
        #             continue
        #
        #         _out_tbl[j]['v'] = 0
        #
        #     avg_years = []
        #     for i, yr in enumerate(years):
        #         if i in exclude_yr_indxs:
        #             continue
        #
        #         for j, d in enumerate(yearlies[yr]['out_tbl']):
        #             if _out_tbl[j]['key'] == 'Total contributing area to outlet':
        #                 continue
        #
        #             v = yearlies[yr]['out_tbl'][j]['v']
        #             if set(str(v).strip()) != set('*'):
        #                 _out_tbl[j]['v'] += v
        #
        #         avg_years.append(yr)
        #
        #     for j, d in enumerate(_out_tbl):
        #         if _out_tbl[j]['key'] == 'Total contributing area to outlet':
        #             continue
        #
        #         _out_tbl[j]['v'] /= float(len(avg_years))
        #
        #     out_tbl = _out_tbl
        #
        #     # average out years for hill table
        #     _hill_tbl = deepcopy(hill_tbl)
        #     for j, d in enumerate(hill_tbl):
        #         for var in hill_hdr[2:]:
        #             _hill_tbl[j][var] = 0
        #
        #     avg_years = []
        #     _avg_years = {}
        #     for i, yr in enumerate(years):
        #         if i in exclude_yr_indxs:
        #             continue
        #
        #         for j, d in enumerate(hill_tbl):
        #             for var in hill_hdr[2:]:
        #
        #                 v = yearlies[yr]['hill_tbl'][j][var]
        #                 if set(str(v).strip()) != set('*'):
        #                     _hill_tbl[j][var] += v
        #
        #                     if var not in _avg_years:
        #                         _avg_years[var] = 0.0
        #                     _avg_years[var] += 1.0
        #
        #         avg_years.append(yr)
        #
        #     for var in hill_hdr[2:]:
        #         _hill_tbl[j][var] /= _avg_years[var]
        #
        #     hill_tbl = _hill_tbl
        #
        #     # average out years for chn table
        #     _chn_tbl = deepcopy(chn_tbl)
        #     for j, d in enumerate(chn_tbl):
        #         for var in chn_hdr[2:]:
        #             _chn_tbl[j][var] = 0
        #
        #     avg_years = []
        #     _avg_years = {}
        #     for i, yr in enumerate(years):
        #         if i in exclude_yr_indxs:
        #             continue
        #
        #         for j, d in enumerate(chn_tbl):
        #             for var in chn_hdr[2:]:
        #
        #                 v = yearlies[yr]['chn_tbl'][j][var]
        #                 if set(str(v).strip()) != set('*'):
        #                     _chn_tbl[j][var] += v
        #
        #                     if var not in _avg_years:
        #                         _avg_years[var] = 0.0
        #                     _avg_years[var] += 1.0
        #
        #         avg_years.append(yr)
        #
        #     for var in chn_hdr[2:]:
        #         _chn_tbl[j][var] /= _avg_years[var]
        #
        #     chn_tbl = _chn_tbl

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

                if isfloat(row['Runoff Volume']):
                    hill_tbl[i]['Runoff'] = 100 * row['Runoff Volume'] / (area * 1000.0)
                else:
                    hill_tbl[i]['Runoff'] = float('nan')

                if isfloat(row[i]['Subrunoff Volume']):
                    hill_tbl[i]['Subrunoff'] = 100 * row['Subrunoff Volume'] / (area * 1000.0)
                else:
                    hill_tbl[i]['Subrunoff'] = float('nan')

                if isfloat(row['Baseflow Volume']):
                    hill_tbl[i]['Baseflow'] = 100 * row['Baseflow Volume'] / (area * 1000.0)
                else:
                    hill_tbl[i]['Baseflow'] = float('nan')

                if isfloat(row['Soil Loss']):
                    _loss = row['Soil Loss'] / area
                else:
                    _loss = float('nan')

                if isfloat(row['Sediment Deposition']):
                    _dep = row['Sediment Deposition'] / area
                else:
                    _dep = float('nan')

                if isfloat(row['Sediment Yield']):
                    _yield = row['Sediment Yield'] / area
                else:
                    _yield = float('nan')

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
                chn_id = row['Channels and Impoundments']

                topaz_id = translator.top(chn_enum=chn_id)
                wepp_id = translator.wepp(chn_enum=chn_id)

                chn_summary = watershed.chn_summary(str(topaz_id))
                area = chn_summary['area'] / 10000.0
                chn_tbl[i]['WeppID'] = chn_id
                chn_tbl[i]['WeppChnID'] = wepp_id
                chn_tbl[i]['TopazID'] = topaz_id
                chn_tbl[i]['Area'] = area
                chn_tbl[i]['Contributing Area'] = row['Contributing Area']
                chn_tbl[i]['Length'] = chn_summary['length']

                if isfloat(row['Sediment Yield']):
                    chn_tbl[i]['Sediment Yield Density'] = row['Sediment Yield'] / area
                else:
                    chn_tbl[i]['Sediment Yield Density'] = float('nan')

                if isfloat(row['Soil Loss']):
                    chn_tbl[i]['Soil Loss Density'] = row['Soil Loss'] / area
                else:
                    chn_tbl[i]['Soil Loss Density'] = float('nan')

                if 'Solub. React. Phosphorus' in row:
                    if isfloat(row['Solub. React. Phosphorus']):
                        chn_tbl[i]['Solub. React. P Density'] = row['Solub. React. Phosphorus'] / area
                    else:
                        chn_tbl[i]['Solub. React. P Density'] = float('nan')

                if 'Particulate Phosphorus' in row:
                    if isfloat(row['Particulate Phosphorus']):
                        chn_tbl[i]['Particulate P Density'] = row['Particulate Phosphorus'] / area
                    else:
                        chn_tbl[i]['Particulate P Density'] = float('nan')

                if 'Total Phosphorus' in row:
                    if isfloat(row['Total Phosphorus']):
                        chn_tbl[i]['Total P Density'] = row['Total Phosphorus'] / area
                    else:
                        chn_tbl[i]['Total P Density'] = float('nan')

        self.fn = fn
        self.hill_tbl = hill_tbl
        self.chn_tbl = chn_tbl
        self.out_tbl = out_tbl
        self.class_data = class_data
        self.wsarea = [d['v'] for d in out_tbl if d['key'] == 'Total contributing area to outlet'][0]
        self.yearlies = yearlies
        self.years = years
        self.num_years = num_years
        if avg_years is None:
            self.avg_years = years
        else:
            self.avg_years = avg_years

        self.has_phosphorus = has_phosphorus

    def outlet_fraction_under(self, particle_size=0.016):
        """

        :param particle_size: in mm
        :return: fraction (0-1) of flow exiting hillslope less than particle size.
        """
        if self.class_data is None:
            return 0.0

        class_data = [(c['Diameter'], c['Fraction In Flow Exiting']) for c in self.class_data]

        class_data.sort(key=lambda x: x[0])

        if particle_size >= class_data[-1][0]:
            return 1.0

        i = 0
        for diam, frac in class_data:
            if particle_size <= diam:
                break
            i += 1

        if i == 0:
            x0 = 0.0
        else:
            x0 = class_data[i-1][0]
        xend, frac = class_data[i]

        partial_frac = (particle_size-x0)/(xend-x0) * frac

        if i > 0:
            for j in range(i):
                partial_frac += class_data[j][1]

        return partial_frac

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


    loss = Loss('/geodata/weppcloud_runs/devvm4b6-394f-4546-bdf9-cab068a50115/wepp/output/loss_pw0.txt',
                '/geodata/weppcloud_runs/devvm4b6-394f-4546-bdf9-cab068a50115/')

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
