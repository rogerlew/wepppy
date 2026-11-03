"""Actual producer, runner and native transition evidence on a committed fixture."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import struct

from wepppy.wepp.management.pmetpara import pmetpara_prep
from wepp_runner.wepp_runner import run_hillslope


def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--binary',required=True)
    parser.add_argument('--output',required=True,type=Path)
    parser.add_argument('--observed',action='store_true')
    parser.add_argument('--reverse-table',action='store_true')
    parser.add_argument('--fixture',required=True,type=Path)
    args=parser.parse_args()
    root=args.output;root.mkdir(parents=True,exist_ok=False)
    fixture=args.fixture
    runs=root/'runs';shutil.copytree(fixture,runs);(root/'output').mkdir()
    path=runs/'p11.man';lines=path.read_text().splitlines()
    year=None;ofe=None
    for i,line in enumerate(lines):
        match=re.search(r'plants/year; <Year: (\d+) - OFE: (\d+)>',line)
        if match: year,ofe=map(int,match.groups())
        if '# yearly index' in line:
            # Rotate the three declared plant scenarios each simulation year.
            lines[i]=f'{(ofe+year-2)%3+1} # yearly index, transition control'
    path.write_text('\n'.join(lines)+'\n')
    kcb={'Tah_4899':.75,'OFE2_Tah_4899':.875,'OFE3_Tah_4899':1.}
    rawp={'Tah_4899':.5,'OFE2_Tah_4899':.625,'OFE3_Tah_4899':.75}
    pmetpara_prep(str(runs),kcb,rawp)
    prepared={p.name:sha(p) for p in runs.iterdir()}
    pmetpara_prep(str(runs),kcb,rawp)
    assert prepared=={p.name:sha(p) for p in runs.iterdir()},'Producer repeat drift'
    if args.reverse_table:
        table=runs/'pmetpara.txt'; rows=table.read_text().splitlines()
        table.write_text('\n'.join(rows[:1]+list(reversed(rows[1:])))+'\n')
    if args.observed: (runs/'mipa_observe.on').touch()
    # Fixture normally uses original Penman. Select existing PMET option in
    # the test run card, keeping production activation defaults unchanged.
    card=runs/'p11.run';cards=card.read_text().splitlines();assert cards[6]=='1'
    cards[6]='2';card.write_text('\n'.join(cards)+'\n')
    inputs={p.name:sha(p) for p in runs.iterdir()}
    result=run_hillslope(11,str(runs),wepp_bin=args.binary,timeout=300,timeout_retries=0)
    assert result[0],result
    outputs={p.name:sha(p) for p in (root/'output').iterdir()}
    assert len(outputs)==7,outputs
    receipt={'binary':args.binary,'binary_sha256':sha(Path(args.binary)),
             'uid':os.getuid(),'gid':os.getgid(),'inputs':inputs,'outputs':outputs,
             'producer_repeat_identical':True,'runner_result':result}
    if args.observed:
        rows=[list(map(int,line.split())) for line in (runs/'mipa-crops.txt').read_text().splitlines()]
        assert len(rows)==48, len(rows)
        for ofe,plant,year,day,kbits,rbits in rows:
            assert 2000 <= year <= 2015, year
            sim_year=year-1999
            expected=(ofe+sim_year-2)%3+1
            assert plant==expected,(ofe,plant,year,expected)
            assert struct.unpack('f',struct.pack('i',kbits))[0]==[.75,.875,1.][plant-1]
            assert struct.unpack('f',struct.pack('i',rbits))[0]==[.5,.625,.75][plant-1]
        receipt['mapped_crop_transitions']=rows
    (root/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
    print(json.dumps({'passed':True,'observed':args.observed,'outputs':len(outputs)}))


if __name__=='__main__': main()
