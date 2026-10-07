"""Read back all retained raw-output hashes and reproduce legacy controls."""
import json
from pathlib import Path
import platform
import subprocess
import sys
import math
import statistics
from importlib.metadata import version
from assess import ROOT, CASES, sha, save, refresh_manifest


def main():
    result={'raw_outputs':{},'historical_reproduction':{},'script_sha256':{}}
    import wepppyo3
    result['environment']={
        'python':sys.version, 'platform':platform.platform(),
        'wepppy_commit':subprocess.check_output(['git','-C','/workdir/wepppy','rev-parse','HEAD'],text=True).strip(),
        'wepppyo3_commit':subprocess.check_output(['git','-C','/workdir/wepppyo3','rev-parse','HEAD'],text=True).strip(),
        'libraries':{n:version(n) for n in ['numpy','pandas','pyarrow','scipy','matplotlib']},
        'native_extensions':{p.name:sha(p) for p in Path(wepppyo3.__file__).parent.glob('*.so')}}
    state=json.loads(Path('/wc1/runs/wa/warming-championship/wepp.nodb').read_text())['py/state']
    result['baseflow_readback']={k:state['baseflow_opts'][k] for k in ['gwstorage','bfcoeff','dscoeff','bfthreshold']}
    assert result['baseflow_readback']==dict(gwstorage=0.,bfcoeff=.04,dscoeff=0.,bfthreshold=1.)
    for lane in CASES:
        case=ROOT/lane
        expected=json.loads((case/'outputs.json').read_text())
        mismatches=[n for n,h in expected.items() if sha(case/'output'/n) != h]
        assert not mismatches, (lane,mismatches)
        result['raw_outputs'][lane]={'checked':len(expected),'mismatches':mismatches}
        for name,h in json.loads((case/'inputs.json').read_text())['sha256'].items():
            assert sha(case/'runs'/name)==h, (lane,name)
        if lane.startswith('legacy'):
            oldlane='rr10' if lane=='legacy10' else 'rr17'
            old=json.loads((Path('/workdir/warming-rrinit-legacy-20261006')/oldlane/'outputs.json').read_text())
            derived={'interchange/H.pass.parquet','interchange/H.wat.parquet','interchange/totalwatsed3.parquet'}
            assert set(old)-set(expected) <= derived
            old={n:h for n,h in old.items() if n not in derived}
            assert set(old)==set(expected)
            changed=[n for n in old if old[n]!=expected[n]]
            result['historical_reproduction'][lane]={'checked':len(old),'changed':changed}
            assert not changed, (lane,changed)
    for name,h in json.loads((ROOT/'source-manifest.json').read_text()).items():
        assert sha(Path('/workdir/warming-rrinit-20261006/snapshot')/name)==h
    for p in Path(__file__).parent.glob('*.py'):
        result['script_sha256'][p.name]=sha(p)
    result['frozen_inputs_unchanged']=True
    import pandas as pd
    reported=json.loads((ROOT/'analysis/metrics.json').read_text())
    baseline=pd.read_parquet(ROOT/'analysis/legacy10-daily.parquet')
    independent={}
    for lane in CASES[1:]:
        candidate=pd.read_parquet(ROOT/'analysis'/(lane+'-daily.parquet'))
        assert baseline.index.equals(candidate.index)
        for field in ['totalwatsed_m3s','channel_m3s']:
            x=baseline[field].tolist();y=candidate[field].tolist()
            mx=statistics.mean(x);my=statistics.mean(y)
            r=statistics.correlation(x,y)
            a=statistics.pstdev(y)/statistics.pstdev(x);b=my/mx
            computed=dict(NSE=1-math.fsum((v-u)**2 for u,v in zip(x,y))/math.fsum((u-mx)**2 for u in x),
                          KGE2009=1-math.sqrt((r-1)**2+(a-1)**2+(b-1)**2),R2=r*r)
            for name,value in computed.items():
                assert abs(value-reported['fits'][lane][field][name]) < 1e-12, (lane,field,name)
            independent[lane+'_'+field]=computed
    result['independent_standard_library_metrics']=independent
    assert json.loads((ROOT/'execution-summary.json').read_text())['observer_parity']
    result['observer_parity']=json.loads((ROOT/'output-mode-parity.json').read_text())
    save(ROOT/'analysis/verification.json',result)
    refresh_manifest()
    print(json.dumps(result,indent=2))


if __name__=='__main__':main()
