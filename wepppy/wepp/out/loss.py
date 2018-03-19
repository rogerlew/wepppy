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

chn_hdr = (
    'Type',
    'Channels and Impoundments',
    'Discharge Volume',
    'Sediment Yield',
    'Soil Loss',
    'Upland Charge',
    'Subsuface Volume',
    'Flow Phosphorus',
    'Solub. Phosphorus',
    'React. Phosphorus',
    'Total Particulate'
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


def parse_cell(v):
    if '.' in v:
        return float(v)

    # noinspection PyBroadException
    try:
        return int(v)
    except Exception:
        return v


class LossReport(object):
    def __init__(self, fn):

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
        
        self.hill_hdr = hill_hdr
        self.chn_hdr = chn_hdr
        
        self.hill_units = hill_units
        self.chn_units = chn_units
        
    def _parse_tbl(self, lines, hdr):
        data = []
        for L in lines:
            if len(L) == 0:
                return data
                
            L = [parse_cell(v) for v in L.split()]
            data.append(dict(zip(hdr, L)))

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
            v = parse_cell(v.strip())

            if key == 'Total contributing area to outlet':
                self.wsarea = v

            data.append(dict(key=key, v=v, units=units))


if __name__ == "__main__":
    report = LossReport('/geodata/weppcloud_runs/dfc452a6-ab62-4233-a98c-194ecb0bba59/wepp/output/loss_pw0.txt')