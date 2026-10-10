#!/usr/bin/env python3
"""Paired release traces with each release's own undisturbed hillslope PASS."""
from concurrent.futures import ThreadPoolExecutor, as_completed
import json
from pathlib import Path
import shutil

import numpy as np
import pandas as pd
from wepppyo3 import wepp_interchange as native

from output_replay import ROOT as PRIOR, SUFFIX, FIELDS, REPO, sha, save, inventory, execute

HERE=Path(__file__).resolve().parent
ROOT=Path('/wc1/holdouts/topanga-jan1993-version-trace-20261009')
SFX=SUFFIX['undisturbed']
CHANNELS=list(range(394,404))+[406,412]
BINARIES={'wepp_260803':'4a5158e224c175ac06c760f1006cc19f7691a9bd28911d94788af2622ba178a5',
          'wepp_260803_hill':'86ef065c8d8c6c1e644db40c022c7c850701c0c174d3c622dfa28f1d6da122e7',
          'wepp_261009':'e1b1c244107216ca9edf4ccbaeb8d390e98440418d87beac2d5153b98191c7cc'}


def run_version(version):
    root=ROOT/version
    source=Path('/wc1/runs/ei/eighty-five-synthetic') if version=='260803' else PRIOR/'control'
    identities={}
    for suffix in (Path(''),SFX):
        src=source/suffix/'wepp/runs';dest=root/suffix/'wepp/runs'
        before=inventory(src);shutil.copytree(src,dest)
        assert before==inventory(dest)==inventory(src)
        identities[str(suffix)]=before
    base=root/SFX/'wepp';(base/'output').mkdir()
    if version=='260803':
        original=pd.read_parquet(source/SFX/'wepp/output/interchange/H.pass.parquet',columns=['wepp_id']+FIELDS)
        refs={int(wid):g[FIELDS].reset_index(drop=True) for wid,g in original.groupby('wepp_id')}
        logs=root/'hillslope-logs';logs.mkdir()
        def hill(wid):
            text,seconds=execute(ROOT/'wepp_260803_hill',base/'runs'/f'p{wid}.run',base/'runs',logs/f'H{wid}.log',300)
            assert 'WEPP COMPLETED HILLSLOPE SIMULATION SUCCESSFULLY' in text
            p=base/'output'/f'H{wid}.pass.dat'
            frame=pd.DataFrame(native.hillslope_pass_to_columns(str(p),1,0))[FIELDS]
            expected=refs[wid]
            assert frame.shape==expected.shape and frame.event.equals(expected.event)
            for column in FIELDS[1:]:
                assert np.array_equal(frame[column],expected[column],equal_nan=True),(wid,column)
            return dict(wepp_id=wid,seconds=seconds,pass_sha256=sha(p),rows=len(frame))
        receipts=[]
        with ThreadPoolExecutor(max_workers=8) as pool:
            for result in as_completed([pool.submit(hill,wid) for wid in range(1,285)]):
                receipts.append(result.result())
                if len(receipts)%32==0:print('OLD HILLS',len(receipts),'/284',flush=True)
        save(root/'hills-receipts.json',receipts)
        del original,refs
    else:
        prior={r['wepp_id']:r for r in json.loads((PRIOR/'hills-receipts.json').read_text()) if r['scenario']=='undisturbed'}
        for wid in range(1,285):
            p=source/SFX/'wepp/output'/f'H{wid}.pass.dat'
            assert sha(p)==prior[wid]['pass_sha256']
            (base/'output'/p.name).symlink_to(p)
    (base/'runs/chan.inp').write_text('3 600\n0\n'+str(len(CHANNELS))+'\n'+' '.join(map(str,CHANNELS))+'\n')
    after=inventory(base/'runs');before=identities[str(SFX)]
    assert {n for n in before if before[n]!=after[n]}=={'chan.inp'}
    save(root/'input-identities.json',identities)
    text,seconds=execute(ROOT/f'wepp_{version}',base/'runs/pw0.run',base/'runs',root/'watershed.log',1800)
    assert 'WEPP COMPLETED WATERSHED SIMULATION SUCCESSFULLY' in text
    for name in ('chan.out','chanwb.out','tc_out.txt'):
        shutil.move(str(base/'runs'/name),base/'output'/name)
    parsed=root/'ebe.parquet'
    native.watershed_ebe_to_parquet(str(base/'output/ebe_pw0.txt'),str(parsed),1,0,start_year=1980,legacy_element_id=412)
    frame=pd.read_parquet(parsed);outlet=frame.loc[frame.element_id.eq(412)].reset_index(drop=True)
    if version=='260803':
        expected=pd.read_parquet(HERE/'artifacts/260803-comparison/260803-undisturbed-ebe.parquet')
    else:
        expected=pd.read_parquet(REPO/'docs/investigations/2026-10-09-watershed-return-period-comparisons/artifacts/snapshot/topanga_gridmet_261009_undisturbed.parquet')
    assert len(outlet)==len(expected)==16437
    for column in ('year','month','day_of_month','runoff_volume','peak_runoff','sediment_yield'):
        assert np.array_equal(outlet[column],expected[column],equal_nan=True),(version,column)
    save(root/'receipt.json',dict(version=version,seconds=seconds,outlet_parity='exact frozen EBE fields',
        selected_elements=CHANNELS,rows=len(frame),output_hashes=inventory(base/'output')))
    print('VERSION',version,'complete; frozen outlet parity verified',flush=True)


def main():
    ROOT.mkdir(parents=True,exist_ok=False)
    for name,expected in BINARIES.items():
        source=REPO/'wepp_runner/bin'/name;assert sha(source)==expected
        shutil.copy2(source,ROOT/name)
    shutil.copy2(__file__,ROOT/'executed_runner.py')
    with ThreadPoolExecutor(max_workers=2) as pool:
        list(pool.map(run_version,['260803','261009']))


if __name__=='__main__':
    main()
