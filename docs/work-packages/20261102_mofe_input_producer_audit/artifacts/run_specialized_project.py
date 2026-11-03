"""Execute and read the completely prepared disposable specialized project."""
from pathlib import Path
import hashlib,json,os,shutil
import pyarrow.parquet as pq
from wepppy.nodb.core import Wepp, Climate
from wepp_runner.wepp_runner import get_linux_wepp_bin_role_paths
from wepppy.wepp.interchange import run_wepp_hillslope_interchange
from wepppy.wepp.reports.hillslope_watbal import HillslopeWatbalReport

WD=Path('/wc1/runs/mi/mipa-rap-20261103')
EVIDENCE=Path('/wc1/holdouts/mipa-native-r7-20261103/configured-execution-v1')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    EVIDENCE.mkdir(exist_ok=False)
    w=Wepp.getInstance(str(WD)); c=Climate.getInstance(str(WD))
    runs=Path(w.runs_dir);output=Path(w.output_dir)
    settings={k:getattr(w,k) for k in ('run_frost','run_baseflow','run_wepp_ui','run_pmet','run_snow','multi_ofe')}
    roles={str(p):sha(Path(p)) for p in get_linux_wepp_bin_role_paths(w.wepp_bin)}
    inputs={p.name:sha(p) for p in runs.iterdir() if p.is_file() and p.suffix!='.err'}
    assert len(list(runs.glob('p*.cov')))==72
    assert (runs/'firedate.txt').read_text()=='6 1 2005\n'
    assert all((runs/name).exists() for name in ['gwcoeff.txt','wepp_ui.txt','cancov.txt','simfire.txt'])
    (EVIDENCE/'inputs.json').write_text(json.dumps(inputs,indent=2)+'\n')
    (EVIDENCE/'context.json').write_text(json.dumps({'uid':os.getuid(),'gid':os.getgid(),
        'groups':os.getgroups(),'settings':settings,'roles':roles,'wd':str(WD)},indent=2)+'\n')
    if output.exists():
        output.rename(EVIDENCE/'prior-output')
    output.mkdir()
    w.run_hillslopes(max_workers=4)
    outputs={p.name:sha(p) for p in output.iterdir() if p.is_file()}
    assert len(outputs)==504,len(outputs)
    logs={p.name:sha(p) for p in runs.glob('p*.err')}
    assert len(logs)==72,len(logs)
    for p in runs.glob('p*.err'):
        text=p.read_text()
        assert 'WEPP COMPLETED HILLSLOPE SIMULATION SUCCESSFULLY' in text,p
    result=run_wepp_hillslope_interchange(output,pass_family='legacy_ascii',start_year=c.calendar_start_year,
        delete_after_interchange=False,max_workers=4)
    report=HillslopeWatbalReport(WD)
    assert len(report.areas)==72 and len(report.years)>=35
    datasets={p.name:{'sha256':sha(p),'rows':pq.ParquetFile(p).metadata.num_rows} for p in result.glob('*.parquet')}
    assert inputs=={p.name:sha(p) for p in runs.iterdir() if p.is_file() and p.suffix!='.err'}
    (EVIDENCE/'receipt.json').write_text(json.dumps({'outputs':outputs,'logs':logs,'datasets':datasets,
        'report_hills':len(report.areas),'report_years':report.years,'area_m2':report.wsarea},indent=2)+'\n')
    print('PASS complete specialized configured execution and report readback',flush=True)
if __name__=='__main__':main()
