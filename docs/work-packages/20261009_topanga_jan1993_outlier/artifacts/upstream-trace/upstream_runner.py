#!/usr/bin/env python3
"""Output-only lower-network trace using validated same-build replay inputs."""
from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
import shutil

import pandas as pd

from output_replay import ROOT, SUFFIX, HASHES, inventory, lane, execute, save, sha

HERE = Path(__file__).resolve().parent
CHANNELS = list(range(404,413))


def main():
    assert sha(ROOT/'wepp_261009') == HASHES['wepp_261009']
    assert not (ROOT/'upstream').exists()
    prior=json.loads((ROOT/'watershed-receipts.json').read_text())
    assert len(prior)==2 and all(not r['observer_differences'] for r in prior)
    topology=[]
    lines=(lane('control','burned')/'runs/pw0.str').read_text().splitlines()
    for wepp_id,line in enumerate(lines[1:],285):
        fields=list(map(int,line.split()))
        assert len(fields)==10 and fields[0]==2
        if wepp_id in CHANNELS:
            topology.append(dict(wepp_id=wepp_id,hillslopes=fields[1:4],upstream_channels=fields[4:7]))
    assert len(topology)==9
    mapping=pd.read_parquet('/wc1/runs/sc/scrawny-relay/watershed/channels.parquet')
    save(ROOT/'upstream-selection.json',dict(selected_elements=CHANNELS,topology=topology,
        mapping=mapping.loc[mapping.wepp_id.isin(CHANNELS),['wepp_id','topaz_id','chn_enum','length','slope_scalar','width']].to_dict('records')))
    for scenario in SUFFIX:
        source=lane('control',scenario);target=lane('upstream',scenario)
        shutil.copytree(source/'runs',target/'runs')
        (target/'output').mkdir()
        for wid in range(1,285):
            p=source/'output'/f'H{wid}.pass.dat'
            (target/'output'/p.name).symlink_to(p)
        (target/'runs/chan.inp').write_text('3 600\n0\n9\n'+' '.join(map(str,CHANNELS))+'\n')
        a=inventory(source/'runs');b=inventory(target/'runs')
        assert {n for n in a if a[n]!=b[n]}=={'chan.inp'}
    shutil.copy2(__file__,ROOT/'upstream_runner.py')
    def run(scenario):
        target=lane('upstream',scenario);source=lane('control',scenario)
        text,seconds=execute('wepp_261009',target/'runs/pw0.run',target/'runs',ROOT/f'{scenario}-upstream.log',1800)
        assert 'WEPP COMPLETED WATERSHED SIMULATION SUCCESSFULLY' in text
        for name in ('chan.out','chanwb.out','tc_out.txt'):
            shutil.move(str(target/'runs'/name),target/'output'/name)
        a=inventory(source/'output');b=inventory(target/'output')
        common=sorted(set(a)&(set(b)-{'chan.out','chanwb.out'}))
        different=[name for name in common if a[name]!=b[name]]
        assert not different,(scenario,different)
        record=dict(scenario=scenario,seconds=seconds,compared_files=common,differences=different,output_sha256=b)
        save(ROOT/f'{scenario}-upstream-receipt.json',record)
        print(scenario,'complete; observer-neutral across',len(common),'files',flush=True)
    with ThreadPoolExecutor(max_workers=2) as pool:
        list(pool.map(run,SUFFIX))


if __name__=='__main__':
    main()
