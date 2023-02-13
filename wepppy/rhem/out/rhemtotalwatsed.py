from os.path import join as _join
import pandas as pd


class RhemTotalWatSed:
    def __init__(self, wd):
        from wepppy.nodb import Watershed, Rhem, Climate
        from wepppy.rhem.out import RhemOutput

        self.wd = wd

        watershed = Watershed.getInstance(wd)
        rhem = Rhem.getInstance(wd)

        d = None
        total_area_m2 = 0.0
        for topaz_id, ss in watershed.subs_summary.items():
            print(ss)
            area_m2 = ss['area']
            area_ha = area_m2 / 10000.0
            total_area_m2 += area_m2

            out_fn = _join(rhem.output_dir, f'hill_{topaz_id}.out')
            out = RhemOutput(out_fn)

            if d is None:
                d = pd.DataFrame()
                for cname, units in zip(out.cnames, out.units):
                    if 'mm' == units:
                        d[f'{cname} (m^3)'] = out[cname] * area_m2
                    elif 'mm/hr' == units:
                        d[f'{cname} (m^3/hr)'] = out[cname] * area_m2
                    elif 'ton/ha' == units:
                        d[f'{cname} (tonne)'] = out[cname] * area_ha
                    elif 'min' == units:
                        d[f'{cname} (min/ha)'] = out[cname] / area_ha
                    else: 
                        d[cname] = out[cname]

            for cname, units in zip(out.cnames, out.units):
                if 'mm' == units:
                    d[f'{cname} (m^3)'] += out[cname] * area_m2
                elif 'mm/hr' == units:
                    d[f'{cname} (m^3/hr)'] += out[cname] * area_m2
                elif 'ton/ha' == units:
                    d[f'{cname} (tonne)'] += out[cname] * area_ha
                elif 'min' == units:
                    d[f'{cname} (min/ha)'] += out[cname] / area_ha

        total_area_ha = total_area_m2 / 10000.0
        for cname, units in zip(out.cnames, out.units):
            if 'mm' == units:
                d[f'{cname} (mm)'] = d[f'{cname} (m^3)'] / total_area_m2 * 1000.0
            elif 'mm/hr' == units:
                d[f'{cname} (mm/hr)'] = d[f'{cname} (m^3/hr)'] / total_area_m2 * 1000.0
            elif 'ton/ha' == units:
                d[f'{cname} (tonne/ha)'] = d[f'{cname} (tonne)'] / total_area_ha
        

        by_date = {}
        for index, row in d.iterrows():
            by_date[(row['Day'], row['Month'], row['Year'])] = row

        d.attrs['wsarea'] = total_area_m2
        d.to_pickle(_join(rhem.output_dir, 'rhemtotalwatsed.pkl'))
        self.wsarea = total_area_m2
        self.d = d

    def export(self, fn):
        d = self.d
        for k in d.keys():
            if '(m^3)' in k:
                del d[k]

        with open(fn, 'w') as fp:
            fp.write('DAILY TOTAL WATER BALANCE AND SEDIMENT\n\n')
            fp.write(f'Total Area (m^2): {self.wsarea}\n\n')

            wtr = csv.DictWriter(fp,
                                 fieldnames=list(d.keys()),
                                 lineterminator='\n')
            wtr.writeheader()
            for i, yr in enumerate(d['Year']):
                wtr.writerow(OrderedDict([(k, d[k][i]) for k in d]))                         
