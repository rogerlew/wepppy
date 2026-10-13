"""Retain annual actual WEPP flux/storage diagnostics, with explicit closure limits."""
import json
from pathlib import Path

import numpy as np
import pandas as pd

from workflows import HERE,ROOT


def main():
    rows=[]
    for parent in [ROOT/'workflows-full',ROOT/'canadian-full']:
        for record in parent.glob('**/execution.json'):
            state=json.loads(record.read_text())
            if state['status']!='complete':continue
            paths=list((record.parent/'output').glob('H*.wat.dat'))
            if len(paths)!=1:raise ValueError('Expected one hillslope water output')
            data=[]
            for line in paths[0].read_text().splitlines():
                fields=line.split()
                if len(fields)==25 and fields[0].isdigit():data.append([float(v) for v in fields])
            data=np.asarray(data)
            # Fluxes are daily mm; storage uses total_soil_water + SWE.
            for year in sorted(set(data[:,2].astype(int))):
                mask=data[:,2]==year;part=data[mask]
                p,runoff,et,deep,lateral=(part[:,3].sum(),part[:,5].sum(),part[:,6:9].sum(),part[:,9].sum(),part[:,12].sum())
                indices=np.flatnonzero(mask);previous=indices[0]-1
                storage_change=None if previous<0 else float(data[indices[-1],20]+data[indices[-1],15]-data[previous,20]-data[previous,15])
                residual=None if storage_change is None else float(p-runoff-et-deep-lateral-storage_change)
                rows.append(dict(case=str(record.parent.relative_to(ROOT)),year=year,days=len(part),p_mm=p,
                                 runoff_mm=runoff,et_mm=et,deep_mm=deep,lateral_mm=lateral,
                                 end_soil_water_mm=float(part[-1,20]),end_swe_mm=float(part[-1,15]),
                                 soil_snow_storage_change_mm=storage_change,partial_balance_residual_mm=residual))
    pd.DataFrame(rows).to_csv(HERE/'annual-water-diagnostics.csv',index=False)
    print(len(rows),'case-years; partial residual excludes unreported canopy/snow-vapor/other storage and flux terms')


if __name__=='__main__':main()
