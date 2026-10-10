#!/usr/bin/env python3
"""Run a date-filtered observer build; require unchanged watershed outputs."""
from pathlib import Path
import shutil

from output_replay import ROOT as PRIOR, SUFFIX, inventory, execute, save, sha

ROOT=Path('/wc1/holdouts/topanga-jan1993-version-trace-20261009')


def main():
    destination=ROOT/'observer'
    assert not destination.exists()
    for suffix in (Path(''),SUFFIX['undisturbed']):
        source=PRIOR/'control'/suffix/'wepp/runs'
        target=destination/suffix/'wepp/runs'
        shutil.copytree(source,target)
        assert inventory(source)==inventory(target)
    base=destination/SUFFIX['undisturbed']/'wepp'
    control=PRIOR/'control'/SUFFIX['undisturbed']/'wepp'
    (base/'output').mkdir()
    for wid in range(1,285):
        p=control/'output'/f'H{wid}.pass.dat'
        (base/'output'/p.name).symlink_to(p)
    (base/'runs/wepp_observe.on').touch()
    binary=ROOT/'observer-source/wepp'
    save(destination/'build.json',dict(binary_sha256=sha(binary),
        source_commit='692c225e672844c71114bbdda851625616ebbba9',
        changed_source_sha256={n:sha(ROOT/'observer-source'/n) for n in ['wshchr.for','wepp_observe.for']},
        scope='observer-only calls and January 16-18, 1993 date filter; no equation/state mutation'))
    text,seconds=execute(binary,base/'runs/pw0.run',base/'runs',destination/'watershed.log',1800)
    assert 'WEPP COMPLETED WATERSHED SIMULATION SUCCESSFULLY' in text
    for name in ('chan.out','chanwb.out','tc_out.txt'):
        shutil.move(str(base/'runs'/name),base/'output'/name)
    a=inventory(control/'output');b=inventory(base/'output')
    common=sorted(set(a)&set(b));different=[n for n in common if a[n]!=b[n]]
    save(destination/'receipt.json',dict(seconds=seconds,compared_files=common,differences=different,
        output_sha256=b,observer_log_sha256=sha(base/'runs/wepp_observe.log')))
    assert not different,different
    print('Observer-neutral across',len(common),'output files; full45year reproduction verified',flush=True)


if __name__=='__main__':
    main()
