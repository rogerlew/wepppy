"""Read retained failed-workflow v1 outputs; never run native code or converters."""
from collections import Counter, defaultdict
from datetime import date, timedelta
from pathlib import Path
import hashlib
import json
import math
import re

import pyarrow as pa
import pyarrow.compute as pc
import pyarrow.parquet as pq

from audit_pass_completeness_r7 import daily_records

ROOT = Path('/wc1/runs/ro/roads-parameterization-program-20261103/current-project-v1')
ART = Path(__file__).resolve().parent


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def inventory(root):
    return {str(p.relative_to(root)): sha(p) for p in sorted(root.rglob('*')) if p.is_file()}


def main():
    project = ROOT / 'baseline'
    runs, output = project / 'wepp/runs', project / 'wepp/output'
    before = {'runs': inventory(runs), 'output': inventory(output)}
    declaration_path = ROOT / 'baseline-execution-declaration-v3.json'
    declaration = json.loads(declaration_path.read_text())
    assert all(sha(project / name) == value for name, value in declaration['inputs'].items())
    start = json.loads((ROOT / 'baseline-execution-start.json').read_text())
    assert start['declaration_sha256'] == sha(declaration_path)
    expected = {date(2000, 1, 1) + timedelta(days=i) for i in range(5844)}
    hills, notices = [], {}
    for identifier in list(range(1, 67)) + ['w0']:
        trace_path = runs / f'p{identifier}.err'
        trace = trace_path.read_text()
        watershed = identifier == 'w0'
        role = 'WATERSHED' if watershed else 'HILLSLOPE'
        binary = 'wepp_261029' if watershed else 'wepp_261029_hill'
        assert f'binary_sha256={declaration["binaries"][binary]}' in trace
        assert 'binary_identity_status=ok' in trace
        assert f'WEPP COMPLETED {role} SIMULATION SUCCESSFULLY' in trace
        assert all(marker in trace for marker in (
            '->Gwcoeff parameters set', '->WEPP hourly water seepage update set (UI code)',
            'FAO Penman-Monteith ET Method Implemented'))
        assert list(map(int, re.findall(r'SIMULATION YEAR =\s*(\d+)', trace))) == list(range(1, 17))
        assert not re.search(r'attempt [2-9]/', trace)
        if 'No Penman-Monteith ET parameters' in trace:
            begin = trace.index('*************** Notice')
            end = trace.index('FAO Penman-Monteith ET Method Implemented', begin)
            notices[trace_path.name] = trace[begin:end].strip()
        if watershed:
            continue
        lines = (output / f'H{identifier}.pass.dat').read_text().splitlines()
        assert lines[0] == 'WEPP_PASS_COMPONENTS 3'
        assert lines[1].strip() == f'p{identifier}.cli' and lines[2].split() == ['16', '2000']
        records = daily_records(lines)
        assert set(records) == expected
        families = [f'H{identifier}.{family}.dat' for family in
                    ('loss', 'wat', 'soil', 'plot', 'ebe', 'element', 'pass')]
        assert all((output / name).stat().st_size > 0 for name in families)
        hills.append(dict(wepp_id=identifier, calendar_days=len(records), labels=dict(Counter(records.values()))))
    interchange = output / 'interchange'
    water = pq.read_table(interchange / 'H.wat.parquet')
    daily = water.select(['wepp_id', 'ofe_id', 'year', 'julian']).to_pandas()
    expected_tokens = {(day.year, day.timetuple().tm_yday) for day in expected}
    groups = daily.groupby(['wepp_id', 'ofe_id'])
    assert len(groups) == 193
    for _, group in groups:
        assert len(group) == 5844 and set(zip(group.year, group.julian)) == expected_tokens
    nulls = {}
    for field in water.schema:
        if pa.types.is_floating(field.type):
            values = water[field.name]
            assert pc.all(pc.is_finite(pc.drop_null(values))).as_py() is not False
            nulls[field.name] = values.null_count
    elements = pq.read_table(interchange / 'H.element.parquet', columns=['SedLeave'])
    assert pc.all(pc.greater_equal(elements['SedLeave'], 0)).as_py()
    channel_dates = defaultdict(set)
    channel_rows = Counter()
    for line in (output / 'chnwb.txt').read_text().splitlines():
        tokens = line.split()
        if not tokens or not tokens[0].isdigit():
            continue
        assert len(tokens) == 27
        channel, julian, year = map(int, tokens[:3])
        assert all(math.isfinite(float(value)) for value in tokens[3:])
        channel_dates[channel].add((year, julian))
        channel_rows[channel] += 1
    assert channel_dates and all(days == expected_tokens for days in channel_dates.values())
    assert all(count == 5844 for count in channel_rows.values())
    annual = pq.read_table(interchange / 'loss_pw0.all_years.out.parquet')
    assert set(annual['year'].to_pylist()) == set(range(2000, 2016))
    log = (ROOT / 'baseline-run.log').read_text()
    assert 'make_loss_grid' in log and 'No such file or directory' in log
    assert not (ROOT / 'baseline-native-completed.json').exists()
    assert before == {'runs': inventory(runs), 'output': inventory(output)}
    report = dict(workflow_pass=False, failure='Missing wepp/plots during make_loss_grid; canonical clean omitted',
        declaration_sha256=sha(declaration_path), start_sha256=sha(ROOT / 'baseline-execution-start.json'),
        run_log_sha256=sha(ROOT / 'baseline-run.log'), reader_sha256=sha(Path(__file__)),
        binary_sha256=declaration['binaries'], input_integrity=True, review_changed_evidence=False,
        hills=hills, daily_pass_records=sum(h['calendar_days'] for h in hills),
        wat_rows=water.num_rows, wat_ofes=len(groups), water_null_counts=nulls,
        element_rows=elements.num_rows, element_sedleave_nonnegative=True,
        channel_water_rows=sum(channel_rows.values()), channel_count=len(channel_rows),
        channel_dates_complete=True, watershed_annual_years=list(range(2000, 2016)),
        pmet_notices=notices, artifacts=before,
        limits=['No full water/particle closure audit', 'No dynamic snow-consumption trace',
                'No completed watershed interchange/workflow claim',
                'PMET channel fallback retained explicitly; coefficients do not discriminate ownership'])
    target = ART / 'resumption-r7-current-project-v1-native-readback.json'
    with target.open('x') as stream:
        json.dump(report, stream, indent=2, allow_nan=False)
        stream.write('\n')
    print(json.dumps({key: report[key] for key in ('workflow_pass', 'daily_pass_records', 'wat_rows',
          'wat_ofes', 'channel_water_rows', 'channel_count', 'pmet_notices')}))


if __name__ == '__main__':
    main()
