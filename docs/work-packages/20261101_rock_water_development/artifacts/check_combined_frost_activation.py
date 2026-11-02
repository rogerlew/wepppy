"""Original mutation controls; no model execution."""
import copy
import json
from pathlib import Path
import tempfile
import read_combined_frost_activation as reader


def run():
    checks = []
    def reject(name, fn):
        try:
            fn()
        except ValueError:
            checks.append(name)
        else:
            raise AssertionError(name)
    def row(tag, index=0, stage=None, part=None):
        return dict(year=1, day=1, ofe=1, tag=tag, index=index, snapshot=stage, group=part, values=[1])
    def snapshot(stage):
        return [row(stage+'_'+p, 1 if p == 'LAYER' else 0, stage, p) for p in ('LAYER','PLANT','WATER','STATE')]
    hours = [row(t,h) for h in range(1,25) for t in ('WINTER_SNOW_PRE','SNOW_ENTRY','SNOW_RETURN','WINTER_SNOW_POST','WINTER_MELT_HOUR')]
    rows = snapshot('DAY_OPEN') + snapshot('WINTER_PRE') + hours + [row('WINTER_RETURN')] + snapshot('WINTER_POST') + snapshot('DAY_CLOSE')
    census = reader.census_rows(rows, [[1,1]], 1)
    assert census['hourly_fullperiod_observed']
    checks.append('complete actual hourly census')
    coarse = [r for r in rows if r not in hours]
    assert not reader.census_rows(coarse, [[1,1]], 1)['hourly_fullperiod_observed']
    checks.append('unobserved hours explicitly absent')
    for name, mutated in [('missing hour', rows[:8]+rows[9:]), ('duplicate hour',rows[:8]+[rows[8]]+rows[8:]), ('truncated post',rows[:-5]), ('missing return',[r for r in rows if r['tag']!='WINTER_RETURN']), ('extra date',[dict(r,day=2) for r in rows]), ('missing daily close',rows[:-4])]:
        reject(name, lambda m=mutated: reader.census_rows(m,[[1,1]],1))
    with tempfile.TemporaryDirectory() as temp:
        path=Path(temp)/'frost.log'
        good='WFR_SUM_CALL y=1 d=1 e=1 c=0 s=0 v1=2.4000E+01 v2=2.4000E+01\nWFR_SUM_GUAR y=1 d=1 e=1 c=0 s=0 v1=0.0000E+00 v2=0.0000E+00\n'
        path.write_text(good); assert reader.validate_frost(path,census)['executed']==0
        checks.append('eligible all skipped')
        path.write_text(good.replace('2.4000E+01','0')); assert reader.validate_frost(path,census)['eligible']==0
        checks.append('zero eligibility legitimate')
        mutations={'executed':good.replace('v2=2.4000E+01','v2=23'), 'guard':good.replace('v1=0.0000E+00','v1=1'), 'missing':good.splitlines()[0]+'\n', 'duplicate':good+good.splitlines()[0]+'\n', 'unknown tag':good.replace('WFR_SUM_GUAR','LOC_BAD'), 'extra clock':good.replace('d=1','d=2'), 'channel':good.replace('c=0','c=1'), 'fractional':good.replace('2.4000E+01','0.5'), 'nonfinite':good.replace('2.4000E+01','NaN'), 'overflow':good.replace('2.4000E+01','25'), 'negative':good.replace('2.4000E+01','-1'), 'trailing data':good+'garbage\n', 'blank':good+'\n'}
        for name, text in mutations.items():
            path.write_text(text)
            reject(name,lambda:reader.validate_frost(path,census))
        path.write_text(good)
        duplicate=copy.deepcopy(census);duplicate['records']*=2
        reject('duplicate expected key',lambda:reader.validate_frost(path,duplicate))
    return dict(passed=True, controls=checks, count=len(checks))

if __name__ == '__main__':
    print(json.dumps(run(),indent=2))
