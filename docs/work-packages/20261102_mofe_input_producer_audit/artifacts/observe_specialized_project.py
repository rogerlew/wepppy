"""Observe representative actual prepared decks without parallel trace collisions."""
from pathlib import Path
import hashlib,json,shutil,subprocess,math
import numpy as np
from wepp_runner.wepp_runner import get_linux_wepp_bin_role_paths
from wepppy.wepp.soils.utils import WeppSoilUtil

SOURCE=Path('/wc1/runs/mi/mipa-rap-20261103/wepp')
ROOT=Path('/wc1/holdouts/mipa-native-r7-20261103/configured-observation-v1')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    ROOT.mkdir(exist_ok=False)
    counts={p.stem: (len(p.read_text().splitlines())-1)//6 for p in (SOURCE/'runs').glob('p*.cov')}
    # Include single and longest hill, then a distinct remaining MOFE case.
    ordered=sorted(counts,key=lambda k:(counts[k],int(k[1:])))
    selected=list(dict.fromkeys([ordered[0],ordered[-1],ordered[len(ordered)//2]]))
    binary=Path(get_linux_wepp_bin_role_paths('wepp_261029')[1])
    receipt={'binary_sha256':sha(binary),'selected':selected,'cases':{}}
    for name in selected:
        case=ROOT/name;runs=case/'runs'
        shutil.copytree(SOURCE/'runs',runs)
        (case/'output').mkdir()
        (runs/'wepp_observe.on').touch()
        with (runs/(name+'.run')).open('rb') as stdin:
            r=subprocess.run([str(binary)],stdin=stdin,cwd=runs,capture_output=True,timeout=300)
        (case/'stdout').write_bytes(r.stdout);(case/'stderr').write_bytes(r.stderr)
        assert r.returncode==0 and b'WEPP COMPLETED HILLSLOPE SIMULATION SUCCESSFULLY' in r.stdout,name
        outputs={p.name:sha(p) for p in (case/'output').iterdir()}
        assert len(outputs)==7
        assert all(sha(SOURCE/'output'/k)==v for k,v in outputs.items()),name
        rows=[line.split() for line in (runs/'wepp_rap_read.csv').read_text().splitlines()]
        assert list(map(int,rows[0][3:6]))==[2005,152,1],rows[0]
        bands=rows[1:]
        emitted=[list(map(float,line.split())) for line in (runs/(name+'.cov')).read_text().splitlines()[1:]]
        assert len(bands)==6*counts[name]==len(emitted)
        for observed,expected in zip(bands,emitted):
            assert np.allclose(list(map(float,observed[4:])),np.asarray(expected,dtype=np.float32),rtol=6e-8,atol=0)
        soil=[line.split() for line in (runs/'wepp_rap_dynamic.csv').open() if line.startswith(' SOIL')]
        # Parse the same real writer deck through its owned reader, then compare native state.
        deck=WeppSoilUtil(str(runs/(name+'.sol')))
        native=[]
        for row in soil:
            values=list(map(float,row[4:]));assert all(map(math.isfinite,values));native.append(values)
        assert len(native)==counts[name]
        for values,ofe in zip(native,deck.obj['ofes']):
            expected=[float(ofe[key]) for key in ('texid_enum','uksat','lkeff')]
            assert np.allclose(values[:3],expected,rtol=6e-8,atol=0),(name,values,expected)
        receipt['cases'][name]={'ofes':counts[name],'cover_bands':len(bands),'native_soil_values':native,
            'read_sha256':sha(runs/'wepp_rap_read.csv'),'dynamic_sha256':sha(runs/'wepp_rap_dynamic.csv'),
            'outputs':outputs,'observer_neutral':True}
    (ROOT/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
    print('PASS actual consumed cover states and observer-neutral configured outputs')
if __name__=='__main__':main()
