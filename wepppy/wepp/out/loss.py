
report_hill_hdr = (
    'TopazID',
    'Length',
    'Hillslope Area',
    'Subrunoff',
    'Baseflow',
    'Soil Loss Density',
    'Sediment Deposition Density',
    'Sediment Yield Density',
    'Solub. React. P Density',
    'Particulate P Density',
    'Total P Density'
)

report_hill_units = (
    None,
    'm',
    'ha',
    'mm',
    'm^3',
    'tonne/ha',
    'tonne/ha',
    'tonne/ha',
    'kg/ha',
    'kg/ha',
    'kg/ha'
)

hill_hdr = (
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

hill_units = (
    None, None, 'm^3', 'm^3', 'm^3', 'kg', 'kg', 'kg', 'ha', 'kg', 'kg', 'kg'
)


report_chn_hdr = (
    'TopazID',
    'Length',
    'Area',
    'Discharge Volume',
    'Sediment Yield',
    'Soil Loss',
    'Upland Charge',
    'Subsuface Volume',
    'Flow Phosphorus',
    'Solub. React. P Density',
    'Particulate P Density',
    'Total P Density'
)

report_chn_units = (
    None, 'm', 'ha', 'm^3', 'tonne', 'kg', 'm^3', 'm^3', 'm^3', 'kg', 'kg', 'kg'
)

chn_hdr = (
    'Type',
    'Channels and Impoundments',
    'Discharge Volume',
    'Sediment Yield',
    'Soil Loss',
    'Upland Charge',
    'Subsuface Volume',
    'Flow Phosphorus',
    'Solub. React. Phosphorus',
    'Particulate Phosphorus',
    'Total Phosphorus'
)

chn_units = (
    None, None, 'm^3', 'tonne', 'kg', 'm^3', 'm^3', 'kg', 'kg', 'kg', 'kg'
)

unit_consistency_map = {
    'T/ha/yr': 'tonne/ha/yr',
    'tonnes/ha': 'tonne/ha',
    'tonnes/yr': 'tonne/yr',
    None: ''
}


class LossReport(object):
    def __init__(self, fn, wd=None):

        # read the loss report
        with open(fn) as fp:
            lines = fp.readlines()

        # strip trailing and leading white space
        lines = [L.strip() for L in lines]

        # find the average annual
        i0 = 0
        for i0, L in enumerate(lines):
            if 'YEAR AVERAGE ANNUAL VALUES FOR WATERSHED' in L:
                break

        # restrict lines to just the average annual
        # values
        lines = lines[i0+2:]

        # next three tables are the hill, channel, outlet
        # find the table header lines

        header_indx = []

        for i, L in enumerate(lines):
            if L.startswith('----'):
                header_indx.append(i)

        hill0 = header_indx[0] + 1
        chn0 = header_indx[1] + 2 # channel and outlet summary
        out0 = header_indx[2] + 2 # have a blank line before the data

        self.hill_tbl = self._parse_tbl(lines[hill0:], hill_hdr)

        self.chn_tbl = self._parse_tbl(lines[chn0:], chn_hdr)
        self.out_tbl = self._parse_out(lines[out0:])

        self.hill_hdr = report_hill_hdr
        self.chn_hdr = report_chn_hdr
        
        self.hill_units = report_hill_units
        self.chn_units = report_chn_units

        if wd is not None:
            import wepppy

            watershed = wepppy.nodb.Watershed.getInstance(wd)
            translator = watershed.translator_factory()

            for i in range(len(self.hill_tbl)):
                row = self.hill_tbl[i]
                wepp_id = row['Hillslopes']

                topaz_id = translator.top(wepp=wepp_id)
                sub_summary = watershed.sub_summary(str(topaz_id))
                area = row['Hillslope Area']
                self.hill_tbl[i]['TopazID'] = topaz_id
                self.hill_tbl[i]['Length'] = sub_summary['length']
                self.hill_tbl[i]['Runoff'] = row['Runoff Volume'] / area * 1000.0
                self.hill_tbl[i]['Subrunoff'] = row['Subrunoff Volume'] / area * 1000.0
                self.hill_tbl[i]['Baseflow'] = row['Baseflow Volume'] / area * 1000.0
                self.hill_tbl[i]['Soil Loss Density'] = row['Soil Loss'] / 1000.0 / area
                self.hill_tbl[i]['Sediment Deposition Density'] = row['Sediment Deposition'] / 1000.0  / area
                self.hill_tbl[i]['Sediment Yield Density'] = row['Sediment Yield'] / 1000.0 / area

                if 'Solub. React. Phosphorus' in row:
                    self.hill_tbl[i]['Solub. React. P Density'] = row['Solub. React. Phosphorus'] / area

                if 'Particulate Phosphorus' in row:
                    self.hill_tbl[i]['Particulate P Density'] = row['Particulate Phosphorus'] / area

                if 'Total Phosphorus' in row:
                    self.hill_tbl[i]['Total P Density'] = row['Total Phosphorus'] / area

            for i in range(len(self.chn_tbl)):
                row = self.chn_tbl[i]
                wepp_id = row['Channels and Impoundments']

                topaz_id = translator.top(chn_enum=wepp_id)
                chn_summary = watershed.chn_summary(str(topaz_id))
                area = chn_summary['area'] / 10000.0
                self.chn_tbl[i]['TopazID'] = topaz_id
                self.chn_tbl[i]['Area'] = area
                self.chn_tbl[i]['Length'] = chn_summary['length']
                self.chn_tbl[i]['Sediment Yield Density'] = row['Sediment Yield'] / 1000.0 / area
                self.chn_tbl[i]['Soil Loss Density'] = row['Soil Loss'] / 1000.0 / area

                if 'Solub. React. Phosphorus' in row:
                    self.chn_tbl[i]['Solub. React. P Density'] = row['Solub. React. Phosphorus'] / area

                if 'Particulate Phosphorus' in row:
                    self.chn_tbl[i]['Particulate P Density'] = row['Particulate Phosphorus'] / area

                if 'Total Phosphorus' in row:
                    self.chn_tbl[i]['Total P Density'] = row['Total Phosphorus'] / area

                print(topaz_id, row)

    def _parse_tbl(self, lines, hdr):
        data = []
        for L in lines:
            if len(L) == 0:
                return data
                
            row = []

            for v in L.split():
                if v.count('.') == 2:

                    indx = v.find('.')
                    tok0 = v[:indx+3]
                    tok1 = v[indx+3:]

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

            data.append(dict(zip(hdr, row)))

    def _parse_out(self, lines):
        """
        Avg.Ann.Precipitation
        volume in contributing
        area
        19640252

        m3 / yr
        Avg.Ann.irrigation
        volume in contributing
        area
        0

        m3 / yr
        Avg.Ann.water
        discharge
        from outlet
        53559

        m3 / yr
        """

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

            if key == 'Total contributing area to outlet':
                self.wsarea = v

            data.append(dict(key=key, v=v, units=units))


if __name__ == "__main__":
    report = LossReport('/geodata/weppcloud_runs/bb967f25-9fd6-4641-b737-bb10a1cf7843/wepp/output/loss_pw0.txt',
                        '/geodata/weppcloud_runs/bb967f25-9fd6-4641-b737-bb10a1cf7843/')
    print(report.hill_tbl)
    print(report.chn_tbl)