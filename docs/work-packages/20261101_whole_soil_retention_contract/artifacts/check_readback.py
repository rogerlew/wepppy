"""Independent record checks and deliberate corruptions; no builder invocation."""
import copy
import json
import math
import sys
from pathlib import Path

def check(records):
    assert len(records) == 72
    assert len({r['id'] for r in records}) == 72
    for r in records:
        if r['status'] != 'serialized':
            continue
        p = r['prepared']
        assert r['emitted']
        for e in r['emitted']:
            for key, value, digits in [('fc',p['fc'],4),('wp',p['wp'],4),('bd',p['density'],2),('rfg',p['mass_percent'],2)]:
                assert float(e[key]) == float(format(value, f'.{digits}f'))
        for key, source in [('fc','wthirdbar_r'),('wp','wfifteenbar_r')]:
            if r['final_branches'][key] == 'source-capped-mass':
                expected = r['source'][source]/(100-min(50,p['mass_percent']))
                assert math.isclose(p[key], expected, rel_tol=1e-12, abs_tol=1e-14)
        e = r['emitted'][0]
        w = min(.85, float(e['rfg'])/100)
        share = 1/(1 + w*float(e['bd'])/(2.65*(1-w)))
        assert math.isclose(r['emitted_cap_projection']['cpm'], share, rel_tol=1e-12)
        assert r['emitted_cap_projection']['native_executed'] is False

r = json.loads(Path(sys.argv[1]).read_text())['results']
check(r)
mutants = {}
a = copy.deepcopy(r); a.pop(); mutants['missing-case'] = a
a = copy.deepcopy(r); a[-1] = a[-2]; mutants['duplicate-case'] = a
i = next(i for i,x in enumerate(r) if x['status']=='serialized')
a = copy.deepcopy(r); a[i]['emitted'][0]['fc'] += .0001; mutants['precision-drift'] = a
a = copy.deepcopy(r); a[i]['emitted_cap_projection']['cpm'] += .001; mutants['basis-projection-drift'] = a
a = copy.deepcopy(r); a[i]['source']['wthirdbar_r'] += 1; mutants['source-prepared-drift'] = a
for name, data in mutants.items():
    try:
        check(data)
    except AssertionError:
        continue
    raise RuntimeError('Corruption accepted: '+name)
with Path(sys.argv[2]).open('x') as f:
    json.dump(dict(passed=True, real_cases=len(r), rejected_controls=list(mutants)),f,indent=2)
    f.write('\n')
