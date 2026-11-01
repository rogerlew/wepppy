"""Independent observation-only localization readback; never executes WEPP."""
import argparse
from collections import defaultdict
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import struct

HERE = Path(__file__).resolve().parent


def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def read(path):
    return json.loads(Path(path).read_text())


def f32(value):
    return struct.unpack('f', struct.pack('f', value))[0]


def exact(a, b, context):
    assert struct.pack('f', a) == struct.pack('f', b), (context, a, b)


def load(name):
    spec = importlib.util.spec_from_file_location(Path(name).stem, HERE/name)
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    return module


def reconstruct(rows):
    """Check observed native assignments; no unobserved callsite interpolation."""
    geometry = {(r['day'], r['ofe']): r['values'] for r in rows if r['tag'] == 'BP_GEOMETRY'}
    result = {'writeback': [], 'width': [], 'friction': [], 'alpha': [], 'qinf': []}
    final = None; targets = []; writing = None; width = None; candidate = None
    friction = None; latest_friction = {}; latest_alpha = {}; shape = None; qpre = None
    for row in rows:
        tag, day, ip, ix, v = row['tag'], row['day'], row['ofe'], row['index'], row['values']
        if tag == 'RC_FINAL_OWNER':
            assert final is None and writing is None
            assert v[0] == int(v[0]) and v[1] == ip and ix >= int(v[0]) and ix <= ip
            final = row; targets = list(range(int(v[0]), ip+1))
        elif tag == 'RC_WRITE_PRE':
            assert final is not None and writing is None and targets[0] == ip
            assert day == final['day'] and ix == final['index']
            assert v[:2] == [float(final['ofe']), final['values'][0]]
            writing = row
        elif tag == 'RC_WRITE_POST':
            assert writing is not None and (day, ip, ix) == (writing['day'], writing['ofe'], writing['index'])
            pre = writing['values']; assert pre[:2] == v[:2] and pre[4:] == v[4:]
            duration = final['values'][4]
            exact(v[2], duration, 'duration writeback')
            total = geometry[day, ip][2]; assert total > 0
            predicted = f32(f32(f32(v[4]*v[5])/total)/duration) if duration > 0 else 0.0
            exact(v[3], predicted, 'noncontour peak writeback')
            result['writeback'].append({'day': day, 'ofe': ip, 'owner': final['ofe'], 'terminal': ix,
                'group_start': int(v[1]), 'terminal_duration_s': duration,
                'terminal_peak_before_target_loop_m_s': final['values'][5],
                'stored_pre': pre, 'assigned_post': v, 'total_length_m': total,
                'reconstructed_peak_m_s': predicted})
            writing = None; targets.pop(0)
            if not targets: final = None
        elif tag == 'RC_WIDTH_IN':
            assert width is None; width = row; candidate = None
            assert v[0] >= 0 and v[3] > 0
        elif tag == 'RC_WIDTH_CAND':
            assert width is not None and candidate is None and (day, ip) == (width['day'], width['ofe'])
            assert width['values'][4] == 1 and v[0] == width['values'][0] and v[2] == width['values'][2] and v[3] == 1
            candidate = row
        elif tag == 'RC_WIDTH_OUT':
            assert width is not None and (day, ip) == (width['day'], width['ofe'])
            pre = width['values']; assert pre[:2] == v[:2] and pre[3:] == v[3:]
            assert (candidate is not None) == (pre[4] == 1)
            expected = min(max(pre[2], candidate['values'][1]) if candidate else pre[2], pre[3])
            exact(v[2], expected, 'native width selection/cap')
            result['width'].append({'day': day, 'ofe': ip, 'input': pre,
                'candidate': None if candidate is None else candidate['values'], 'output': v,
                'scope': 'Selection/max/cap exact; power-law candidate is the observed native producer value.'})
            width = None; candidate = None
        elif tag == 'RC_FRICTION_IN':
            assert friction is None; friction = row
            assert v[1] > 0
            exact(v[2], f32(v[0]/v[1]), 'rill area fraction')
        elif tag == 'RC_FRICTION_OUT':
            assert friction is not None and (day, ip) == (friction['day'], friction['ofe'])
            pre = friction['values']; assert pre[:4] == v[:4]
            if pre[2] < 1:
                expected = f32(pre[3] + f32(pre[2] * f32(pre[4]-pre[3])))
                exact(v[4], pre[4], 'unchanged rill friction')
            else:
                expected = pre[3]; exact(v[4], pre[3], 'sheet-flow rill friction')
            exact(v[5], expected, 'equivalent friction')
            out = {'day': day, 'ofe': ip, 'input': pre, 'output': v, 'line': row['line']}
            result['friction'].append(out); latest_friction[day, ip] = out; friction = None
        elif tag == 'RC_ALPHA':
            assert ix == 0 and v[2] > 0 and v[3] > 0 and v[4] > 0 and v[5] == 1.5
            consumed = latest_friction[day, ip]
            exact(v[3], consumed['output'][5], 'RDAT consumed friction')
            expected = f32(math.sqrt(f32(f32(f32(v[1]*f32(8.0))*v[2])/v[3])))
            exact(v[0], expected, 'RDAT alpha')
            latest_alpha[day, ip] = row
            result['alpha'].append({'day': day, 'ofe': ip, 'values': v,
                                    'friction_line': consumed['line'], 'line': row['line']})
        elif tag == 'RC_QINF_SHAPE':
            assert shape is None and qpre is None; shape = row
            assert v[0] == 1.5 and v[1] >= 1 and v[2] >= v[1] and v[5] >= 2
            exact(v[3], latest_alpha[day, ip]['values'][0], 'QINF local alpha producer')
            exact(v[4], v[3], 'assigned ALPHAY')
        elif tag == 'RC_QINF_PRE':
            assert shape is not None and qpre is None and (day, ip, ix) == (shape['day'], shape['ofe'], shape['index'])
            if shape['values'][1] == shape['values'][2]:
                exact(v[1], shape['values'][4], 'single-plane effective alpha')
            qpre = row
        elif tag == 'RC_QINF_POST':
            assert qpre is not None and (day, ip, ix) == (qpre['day'], qpre['ofe'], qpre['index'])
            assert qpre['values'][1:] == v[1:], 'Only runoff is mutated by QINF'
            result['qinf'].append({'day': day, 'ofe': ip, 'terminal': ix,
                'shape': shape['values'], 'input': qpre['values'], 'output': v,
                'recession_reduction_m': qpre['values'][0]-v[0]})
            shape = qpre = None
    assert final is writing is width is candidate is friction is shape is qpre is None
    assert not targets
    return result


def pair_rows(left, right, fields):
    output = []
    aa = defaultdict(list); bb = defaultdict(list)
    for row in left: aa[row['day'], row['ofe']].append(row)
    for row in right: bb[row['day'], row['ofe']].append(row)
    for key in sorted(aa.keys() | bb.keys()):
        a, b = aa[key], bb[key]
        if len(a) != len(b):
            output.append({'day_ofe': key, 'off_count': len(a), 'on_count': len(b),
                           'status': 'Different native call support; no one-to-one attribution'})
            continue
        for index, (x, y) in enumerate(zip(a, b)):
            output.append({'day_ofe': key, 'invocation': index,
                'changed_fields': {name: {'off': x[name], 'on': y[name]} for name in fields if x[name] != y[name]},
                'off': x, 'on': y})
    return output


def main():
    ap = argparse.ArgumentParser(); ap.add_argument('--root', type=Path, required=True)
    ap.add_argument('--first-window', action='store_true'); ap.add_argument('--output', type=Path, required=True)
    args = ap.parse_args(); assert not args.output.exists(); root = args.root.resolve()
    d, build, selection = read(root/'execution-declaration.json'), read(root/'build-receipt.json'), read(root.parent/'selection.json')
    assert build['returncode'] == 0 and sha(root/'build/src/wepp') == d['binary_sha256'] == build['binary_sha256']
    for p, h in d['dependencies'].items(): assert sha(p) == h
    for n, h in build['postbuild_inventory'].items(): assert sha(root/'build/src'/n) == h
    gate = root/('preflight.json' if args.first_window else 'verification.json'); assert read(gate)['passed']
    tasks = d['tasks'][:2] if args.first_window else d['tasks']; assert len(tasks) == (2 if args.first_window else 4)
    windows = selection['selectors'][:1] if args.first_window else selection['selectors']
    assert {(t['stratum'], t['mode']) for t in tasks} == {(w['window'], mode) for w in windows for mode in (0, 1)}
    original_reader = load('review_buffer_observer_runtime_r4.py'); particles = load('audit_particle_closure_v2.py')
    refs = {r['mode']: r for r in selection['references']}; result = []; bindings = {}
    for task in tasks:
        folder = Path(task['folder']); ref = refs[task['mode']]; rec = read(folder/'record.json')
        assert all(rec[k] == v for k, v in task.items())
        assert rec['completed'] and rec['returncode'] == 0 and rec['physical_pass']
        assert rec['binary_sha256'] == d['binary_sha256']
        assert sha(ref['record']) == task['source_record_sha256'] == ref['record_sha256']
        old = read(ref['record']); assert rec['outputs'] == task['reference_outputs'] == old['outputs'] and len(rec['outputs']) == 7
        assert rec['metrics'] == old['metrics'] and rec['audit'] == old['audit']
        for n, h in rec['outputs'].items(): assert sha(folder/'output'/n) == sha(Path(ref['record']).parent/'output'/n) == h
        for n, h in (task['inputs'] | task['auxiliary_inputs']).items():
            assert sha(folder/'runs'/n) == sha(Path(ref['record']).parent/'runs'/n) == h
        for n, h in rec['execution_logs'].items(): assert sha(folder/'runs'/n) == h
        assert 'WEPP COMPLETED HILLSLOPE SIMULATION SUCCESSFULLY' in (folder/'runs/stdout').read_text()
        for n, h in rec['observer_files'].items(): assert sha(folder/'observations'/n) == h
        assert sha(folder/'observations/roughness-contract.txt') == sha(ref['state_path']) == ref['state_sha256']
        assert (folder/'observations/roughness-control.txt').read_text() == f"{task['mode']} 3\n"
        assert (folder/'observations/buffer_observe.on').read_text() == f"{task['event']['year']} {task['event']['julian']}\n"
        audit = particles.audit(folder/'record.json'); assert audit == read(folder/'particle-audit.json') and audit['passed'] and not audit['flags']
        trace = folder/'observations/buffer-observation.txt'
        rows = original_reader.trace_rows(trace, task)
        owned = {(r['day'], r['ofe']) for r in rows if r['tag'] == 'BP_OWNER'}
        assert owned == {(day, ip) for day in (task['event']['julian']-1, task['event']['julian']) for ip in (1, 2, 3)}
        reconstructed = reconstruct(rows)
        result.append({'window': task['stratum'], 'mode': task['mode'], 'trace_rows': len(rows),
                       'reconstruction': reconstructed})
        for p in (folder/'record.json', trace, folder/'particle-audit.json', folder/'observations/roughness-contract.txt', Path(ref['record'])):
            bindings[str(p.resolve())] = sha(p)
    comparisons = {}
    for window in windows:
        a, b = sorted([x for x in result if x['window'] == window['window']], key=lambda x:x['mode'])
        comparisons[window['window']] = {name: pair_rows(a['reconstruction'][name], b['reconstruction'][name], fields)
            for name, fields in [('writeback', ('assigned_post',)), ('width', ('input','candidate','output')),
                                 ('friction', ('input','output')), ('alpha', ('values',)), ('qinf', ('input','output'))]}
    persistence = []
    if not args.first_window:
        for mode in (0,1):
            first = next(x for x in result if x['window']=='first_peak' and x['mode']==mode)['reconstruction']
            second = next(x for x in result if x['window']=='next_runoff' and x['mode']==mode)['reconstruction']
            for ip in (1,2):
                widths = [x for x in first['width'] if x['day']==233 and x['ofe']==ip]
                frictions = [x for x in second['friction'] if x['day']==243 and x['ofe']==ip]
                assert widths and frictions
                persistence.append({'mode':mode,'ofe':ip,'last_width_233_m':widths[-1]['output'][2],
                    'first_consumed_width_243_m':frictions[0]['input'][0],
                    'exact':struct.pack('f',widths[-1]['output'][2])==struct.pack('f',frictions[0]['input'][0]),
                    'scope':'Direct equality of observed cross-window values; no claim of observation on intervening days.'})
    for p, h in d['dependencies'].items(): assert sha(p)==h
    for p in (root/'execution-declaration.json',root/'build-receipt.json',root/'observer-map.json',root.parent/'selection.json',gate,
              Path(__file__).resolve(),HERE/'audit_particle_closure_v2.py',HERE/'review_buffer_observer_runtime_r4.py'):
        bindings[str(p.resolve())] = sha(p)
    report={'accepted_runtime_arithmetic_readback':True,'accepted_original_isolation':False,'accepted_parameterization':False,
            'native_runs_by_reviewer':0,'full_period_replays':len(tasks),'ordinary_output_files_exact':7*len(tasks),
            'full_state_traces_exact':len(tasks),'results':result,'mode_comparisons':comparisons,
            'cross_window_width_values':persistence,'scope':'Exact observed assignment and mode-local output parity. Call-count differences remain explicit. Residue attribution and physical correctness of equivalent-plane routing are not established.',
            'bindings':bindings}
    args.output.write_text(json.dumps(report,indent=2,allow_nan=False)+'\n')
    print(json.dumps({'passed':True,'runs':len(tasks),'ordinary_files':7*len(tasks)}))


if __name__=='__main__': main()
