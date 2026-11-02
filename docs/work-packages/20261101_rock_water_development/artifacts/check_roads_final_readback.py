"""Pure negative controls for the bounded Roads reader; no native invocations."""
import copy
import itertools
import io
import json
from unittest.mock import patch, Mock
from pathlib import Path
import read_roads_final as r


def controls():
    passed = []

    def rejects(label, call):
        try:
            call()
        except (ValueError, KeyError):
            passed.append(label)
        else:
            raise AssertionError('Control did not reject: ' + label)

    rows = [dict(case=dict(zip(r.KEYS, k), variant='erosion_road_cap', runtime='project'),
                 reference=2, within=True) for k in itertools.product(*r.VALUES)]
    r.coverage(rows)
    rejects('missing case', lambda: r.coverage(rows[:-1]))
    rejects('duplicate case', lambda: r.coverage(rows + [rows[0]]))
    bad = copy.deepcopy(rows); bad[0]['case']['climate'] = 'unknown'
    rejects('wrong case', lambda: r.coverage(bad))
    bad = copy.deepcopy(rows); bad[0]['case']['runtime'] = 'legacy'
    rejects('wrong conditioning', lambda: r.coverage(bad))
    rejects('invalid reference', lambda: r.within(1, float('nan')))
    failed = copy.deepcopy(rows); failed[0]['within'] = r.within(None, 2)
    assert r.scores(failed)['all']['overall']['cases'] == 840
    assert r.scores(failed)['all']['overall']['passing'] == 839
    assert r.transition(2, None, 2) == dict(regressed=True, recovered=False)
    passed.append('failed case remains denominator and counts as regression')
    rejects('nonfinite', lambda: r.number('NaN'))
    rejects('negative constrained value', lambda: r.number('-1', True))
    dates = {(2003, 1)}
    ef = ['3', '1', '1', '1'] + ['0.000'] * 22
    ef[11] = '*******'
    header = ' '.join(r.ELEMENT) + '\nunits\n'
    def etext(records):
        return header + '\n'.join(' '.join(f) for f in records)
    efs = []
    for o in (1, 2, 3):
        f = ef.copy(); f[0] = str(o); efs.append(f)
    e = r.sparse(etext(efs), 'element', dates, 2003)
    assert len(e) == 3
    r.validate_sm(e, True)
    rejects('candidate Sm star rejected', lambda: r.validate_sm(e, False))
    rejects('duplicate terminal', lambda: r.sparse(etext(efs + [efs[-1]]), 'element', dates, 2003))
    bad = copy.deepcopy(efs); bad[-1][3] = '2003'
    rejects('source versus relative year', lambda: r.sparse(etext(bad), 'element', dates, 2003))
    bad = copy.deepcopy(efs); bad[-1][23] = '*******'
    rejects('star outside Sm', lambda: r.sparse(etext(bad), 'element', dates, 2003))
    bad = copy.deepcopy(efs); bad[-1][23] = 'NaN'
    rejects('nonfinite sparse value', lambda: r.sparse(etext(bad), 'element', dates, 2003))
    changed = copy.deepcopy(e); changed[(2003, 1, 3)][11] = '1000.00'
    changed[(2003, 1, 3)][23] = '0.100'
    differences, _ = r.sparse_changes(e, changed, 'element')
    assert any(f['field'] == 'SedLeave' for d in differences for f in d.get('fields', []))
    assert any(f['kind'] == 'missing_display' for d in differences for f in d.get('fields', []) if 'kind' in f)
    additions, _ = r.sparse_changes({}, e, 'element')
    disappearances, _ = r.sparse_changes(e, {}, 'element')
    assert len(additions) == len(disappearances) == 3
    passed.append('sparse union and Sm row preservation')
    flux = ['0'] * 22; flux[16] = '1.00'
    lines = [' '.join(r.WAT)] + [f'{o} 1 2003 ' + ' '.join(flux) for o in (1, 2, 3)]
    w = r.wat('\n'.join(lines), dates, [1, 1, 1])
    rejects('missing water date', lambda: r.wat('\n'.join(lines[:-1]), dates, [1, 1, 1]))
    rejects('duplicate water date', lambda: r.wat('\n'.join(lines + [lines[-1]]), dates, [1, 1, 1]))
    rejects('water wrong calendar', lambda: r.wat('\n'.join(lines).replace('2003', '1'), dates, [1, 1, 1]))
    slope = '97.3\n3\n100 1\n2 1\n0 0.1 1 0.1\n2 1\n0 0.1 1 0.1\n2 1\n0 0.1 1 0.1\n'
    assert r.geometry(slope, 1, 3) == [1, 1, 1]
    rounded_slope = slope.replace('100 1', '100 43.1052293811319')
    assert r.geometry(rounded_slope, 43.105229381131934, 3) == [43.1052293811319] * 3
    rejects('geometry width beyond print bound', lambda: r.geometry(rounded_slope, 43.1052293811321, 3))
    passed.append('emitted width within half-last-place')
    rejects('profile length beyond printed sum bound', lambda: r.geometry(slope, 1, 6))
    rejects('emitted geometry width mismatch', lambda: r.geometry(slope, 2, 3))
    rejects('wrong width/area', lambda: r.wat('\n'.join(lines), dates, [2, 1, 1]))
    b = copy.deepcopy(w); b[(2003, 1, 1)][0] = -1
    report = r.water_comparison(w, b, [1, 1, 1])
    assert report[0]['negative_new'] == 1
    assert 'old_total_mm' not in next(x for x in report if x['field'] == 'SoilWaterTotal')
    passed.append('signed negative retention and no stock-as-flux total')
    eb = ['1', '1', '1'] + ['0.0'] * 11
    terminal = copy.deepcopy(e); terminal[(2003, 1, 3)][23] = '1.000'
    rejects('missing sparse event', lambda: r.reconcile(terminal, {}, 1, [2003], 1, {2003: 1}))
    event = ['EVENT', '2003', '1'] + ['0.00000E+00'] * 24
    event[7] = '1.00000E+00'; event[15] = '1.00000E+00'
    event[20:25] = ['0.20000E+00'] * 5
    terminal_row = terminal[(2003, 1, 3)]
    assert not r.particle_event(event, terminal_row, 1)['causes']
    strict = event.copy(); strict[20] = '0.20010E+00'
    assert r.particle_event(strict, terminal_row, 1)['causes'] == ['fraction_sum']
    excess = event.copy(); excess[15] = '2.00000E+00'
    assert 'class_bulk_mass' in r.particle_event(excess, terminal_row, 1)['causes']
    zero = event.copy(); zero[15] = '0.00000E+00'
    zero_terminal = terminal_row.copy(); zero_terminal[23] = '0.000'
    assert not r.particle_event(zero, zero_terminal, 1)['causes']
    for index, token in [(7, '-1'), (15, '-1'), (20, 'NaN')]:
        bad = event.copy(); bad[index] = token
        rejects('invalid particle operand ' + str(index), lambda bad=bad: r.particle_event(bad, terminal_row, 1))
    rejects('EVENT token count', lambda: r.particle_event(event[:-1], terminal_row, 1))
    pass_text = 'format\ncli\n1 2003\narea\nparticles\ninit\n' + ' '.join(event) + '\n'
    p = r.particles(pass_text, terminal, dates, 1)
    assert len(p['events']) == 1
    rejects('duplicate EVENT', lambda: r.particles(pass_text + ' '.join(event), terminal, dates, 1))
    rejects('EVENT missing terminal', lambda: r.particles(pass_text, {}, dates, 1))
    sub = pass_text[:pass_text.index('EVENT')] + 'SUBEVENT 2003 1 0 0 0 0 0 0\n'
    p = r.particles(sub, terminal, dates, 1)
    assert len(p['subevents']) == 1 and len(p['no_event']) == 1 and not p['events']
    passed += ['valid Decimal EVENT', 'fraction-only strict flag', 'class/bulk print excess', 'zero sediment', 'SUBEVENT disclosure']
    assert not r.certificate_applicable('same', 'same')
    assert not r.certificate_applicable('old', 'new', True)
    passed.append('old certificate cannot clear changed state or unobserved state')
    candidate_added = {(2003, 2, 3): efs[-1]}
    rejects('candidate new-row Sm star', lambda: r.validate_sm(candidate_added, False))
    r.no_contours('0 # looper; number of Contouring scenarios')
    rejects('nonzero contours', lambda: r.no_contours('1 # looper; number of Contouring scenarios'))
    fake = Mock(); fake.name = 'H1.wat.dat'; fake.open.return_value = io.StringIO('1.***')
    rejects('mixed numeric star', lambda: r.output_scan(fake))
    terminals, ebrows = {}, {}
    for y in (2003, 2004):
        f = terminal_row.copy(); f[23] = '2.000'
        terminals[y, 1, 3] = f
        f = eb.copy(); f[12] = '2.0'; ebrows[y, 1, 3] = f
    annual_check = r.reconcile(terminals, ebrows, 1, [2003, 2004], 2, {2003: 1, 2004: 3})
    assert annual_check['delta_kg_yr'] == 0 and not annual_check['reconciled']
    assert not any(v['reconciled'] for v in annual_check['annual'])
    passed.append('annual errors cannot cancel in mean')
    # Inject a changed digest into the real before/after guard; no file mutation.
    bindings = r.Bindings(); bindings.bind(Path(__file__))
    with patch.object(r, 'sha', return_value='0' * 64):
        rejects('altered output hash', bindings.check)
    return dict(passed=True, controls=passed, count=len(passed), capacity_controls='not executed: internal capacity certification outside this reader scope')


if __name__ == '__main__':
    print(json.dumps(controls(), indent=2))
