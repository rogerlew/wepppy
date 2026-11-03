"""Read fresh native outputs through installed interchange and report consumers."""
from pathlib import Path
import argparse,hashlib,json
import pyarrow.parquet as pq
from wepppy.wepp.interchange import run_wepp_hillslope_interchange
from wepppy.wepp.reports.hillslope_watbal import HillslopeWatbalReport
from wepppy.nodb.core import Climate


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--evidence',default='actual-project-v1')
    args=parser.parse_args()
    wd=Path('/wc1/runs/mi/mipa-awake-20261102')
    climate=Climate.getInstance(str(wd))
    output=wd/'wepp/output'
    result=run_wepp_hillslope_interchange(output,pass_family='legacy_ascii',
        start_year=climate.calendar_start_year,delete_after_interchange=False,max_workers=4)
    report=HillslopeWatbalReport(wd)
    assert len(report.areas)==72,len(report.areas)
    assert len(report.years)>=35,report.years
    datasets={p.name:{'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),
                     'rows':pq.ParquetFile(p).metadata.num_rows} for p in result.glob('*.parquet')}
    evidence=Path('/wc1/holdouts/mipa-native-r6-20261102')/args.evidence/'readback.json'
    evidence.write_text(json.dumps({'datasets':datasets,'report_hills':len(report.areas),
        'report_years':report.years,'area_m2':report.wsarea},indent=2)+'\n')
    print('Native outputs, interchange and report readback PASS')


if __name__=='__main__':main()
