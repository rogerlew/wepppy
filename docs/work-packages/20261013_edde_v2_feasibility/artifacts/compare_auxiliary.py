"""Compare historical hourly EDDE auxiliaries with two one-year CLIGEN pilots."""
import pandas as pd

from wepppy.climates.edde.cligen import read_cli
from wepppy.climates.edde.client import sha256,write_json
from workflows import HERE,ROOT


def main():
    records=[]
    for group,point in [('apostolic-saw','apostolic-saw-h122'),('cryptic-beechnut','cryptic-beechnut-h78')]:
        path=ROOT/'workflows-pilot-v2/WRF-MPI/Historical'/group/'climate/wepp.cli'
        cli=read_cli(path);cli=cli[cli.index.month==1]
        row=dict(group=group,point=point,period='1995-01',model='WRF-MPI',scenario='Historical',cli_sha256=sha256(path))
        for field,column,scale,offset in [('rsds','rad',86400/41840,0),('td','tdew',1,-273.15),('wspds','w-vl',1,0)]:
            native=pd.read_csv(HERE/f'auxiliary-{field}.csv');native=native[native.point==point]
            row[field+'_source_mean']=float(native.value.mean()*scale+offset)
            row[field+'_cligen_mean']=float(cli[column].mean())
        records.append(row)
    write_json(HERE/'auxiliary-station-comparison.json',dict(records=records,
        units={'rsds':'Langleys/day','td':'C','wspds':'m/s'},
        conversions={'rsds':'Mean hourly-sampled W/m2 * 86400 s/day / 41840 J/m2 per Langley; approximate daily energy, diagnostic only','td':'K -273.15'},
        limitation='One historical month at two references; illustrates source/station mismatch, not full-period bias or a future-auxiliary workflow'))


if __name__=='__main__':main()
