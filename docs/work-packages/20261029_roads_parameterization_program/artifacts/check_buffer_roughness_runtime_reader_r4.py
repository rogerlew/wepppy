"""Deterministic synthetic controls for the independent reader; no WEPP runs."""
import argparse
import importlib.util
import json
from pathlib import Path
import struct
import tempfile

ROOT = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('reader', ROOT/'review_buffer_roughness_runtime_r4.py')
r = importlib.util.module_from_spec(spec)
spec.loader.exec_module(r)
f32 = lambda x: struct.unpack('f', struct.pack('f', x))[0]


def synthetic(folder, mode, null=False, change_rh=False):
    task = {'folder': str(folder), 'mode': mode, 'expected_null': null,
            'calendar_first_year': 4, 'calendar_last_year': 4}
    anchor, floor = f32(.1), f32(.006)
    rows = []
    for phase, year, day, ip in r.expected_keys(task):
        pre = anchor if not phase or null or ip != 3 else floor
        post = anchor if mode and ip == 3 else pre
        rh = f32(.02) if change_rh and phase and ip == 3 else anchor
        state = [pre, post, anchor, anchor, anchor, rh]
        values = [('RRC_STATE', 0, state), ('RRC_BITS', 0, [*[r.bits(v) for v in state[:5]], 0]),
                  ('RRC_DENSITY', 1, [1000, 1200, 1000, 100, .4, .9]),
                  ('RRC_DENSITY', 2, [1000, 1200, 1000, 100, .4, .9]),
                  ('RRC_DRIVERS', 0, [day, day, .1, anchor, 0, 0]),
                  ('RRC_CONTEXT', 0, [3, 1, 1, 0, 0 if phase else -1, 1])]
        if phase:
            values.append(('RRC_RESIDUE', 0, [.1, .2, .3, rh, anchor, 10]))
        for tag, index, vv in values:
            rows.append(' '.join(map(str, [tag, phase, year, day, ip, index, mode, *vv]))+'\n')
    path = folder/'observations/roughness-contract.txt'
    path.parent.mkdir(parents=True)
    path.write_text(''.join(rows))
    return task, path, rows


def main():
    ap = argparse.ArgumentParser(); ap.add_argument('--output', type=Path, required=True); args = ap.parse_args()
    assert not args.output.exists()
    results = []
    with tempfile.TemporaryDirectory(prefix='rrc-reader-') as tmp:
        tmp = Path(tmp)
        off, op, _ = synthetic(tmp/'off', 0)
        on, np, original = synthetic(tmp/'on', 1, change_rh=True)
        out = r.compare_contracts(off, on)
        assert out['counts']['daily_calls'] == 366*3
        assert out['endogenous_and_treatment_responses']['RH_m']['different_calls'] == 366
        results.append('complete leap calendar, active restore and endogenous RH accepted')
        def rejected(label, lines):
            np.write_text(''.join(lines))
            try:
                r.compare_contracts(off, on)
            except AssertionError:
                results.append(label)
            else:
                raise AssertionError('Mutation silently accepted: '+label)
        rejected('missing final calendar row rejected', original[:-1])
        rejected('duplicate state row rejected', [original[0], *original])
        lines=original.copy(); f=lines[1].split(); f[7]=str(int(float(f[7]))+1); lines[1]=' '.join(f)+'\n'
        rejected('native REAL bit mismatch rejected', lines)
        lines=original.copy(); f=lines[2].split();f[7]='1001';lines[2]=' '.join(f)+'\n'
        rejected('density drift rejected', lines)
        lines=original.copy(); f=lines[4].split();f[11]='1';lines[4]=' '.join(f)+'\n'
        rejected('configured irrigation rejected', lines)
        lines=original.copy(); f=lines[0].split();f[7]='nan';lines[0]=' '.join(f)+'\n'
        rejected('nonfinite state rejected', lines)
        lines=original.copy(); f=lines[0].split();f[6]='0';lines[0]=' '.join(f)+'\n'
        rejected('wrong mode rejected', lines)
        np.write_text(''.join(original)); on['expected_null']=True
        try:r.compare_contracts(off,on)
        except AssertionError:results.append('unexpected nonidentity in predicted null rejected')
        else:raise AssertionError('Expected-null failure missed')
        assert r.envelope(.1, 1) and r.envelope(1, 1) and not r.envelope(1.0001, 0)
        assert r.envelope(.2, 2) and r.envelope(20, 2) and not r.envelope(.19999, 2) and not r.envelope(20.0001, 2)
        results.append('original envelope equality boundaries and both failure directions preserved')
        a, _, _=synthetic(tmp/'null-off',0,True);b,_,_=synthetic(tmp/'null-on',1,True)
        assert r.compare_contracts(a,b)['counts']['changed_buffer_restores']==0
        results.append('native identity null accepted')
    receipt={'passed': True, 'native_runs':0, 'controls':results,
             'bindings':{str(p):r.sha(p) for p in (Path(__file__).resolve(), ROOT/'review_buffer_roughness_runtime_r4.py')}}
    args.output.write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps({'passed':True,'controls':len(results)}))


if __name__=='__main__':main()
