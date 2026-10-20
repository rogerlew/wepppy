"""Read-only workbook/native audit; writes only the explicitly named JSON receipt."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import tempfile

import openpyxl
import pyarrow as pa
import pyarrow.parquet as pq

parser = argparse.ArgumentParser()
parser.add_argument('--workbook', type=Path, required=True)
parser.add_argument('--native', type=Path, required=True)
parser.add_argument('--output', type=Path, required=True)
args = parser.parse_args()
book = openpyxl.load_workbook(args.workbook, read_only=True, data_only=True)
sheets = {}
for sheet in book.worksheets[1:]:
    rows = sheet.iter_rows(values_only=True)
    columns = {value: index for index, value in enumerate(next(rows)) if value}
    groups = {}
    for row in rows:
        ofe, year, day = (row[columns[key]] for key in ('OFE', 'Y', 'J'))
        if ofe not in (1, 2) or not isinstance(year, (int, float)) or not 1995 <= year <= 2025:
            continue
        if not isinstance(day, (int, float)) or not 1 <= day <= 366:
            continue
        groups.setdefault(int(ofe), []).append({key: row[index] for key, index in columns.items()})
    result = {}
    for ofe, records in groups.items():
        dates = [(row['Y'], row['J']) for row in records]
        annual = {key: sum(row[key] for row in records) / 31 for key in
                  ('P', 'Q', 'QOFE', 'latqcc', 'Ep', 'Es', 'Er', 'Dp', 'UpStrmQ', 'SubRIn')}
        result[ofe] = dict(count=len(records), unique_dates=len(set(dates)),
                           first=dates[0], last=dates[-1], areas=sorted({row['Area'] for row in records}),
                           annual=annual)
    sheets[sheet.title] = result
book.close()
groups = sheets['Two_OFE']
areas = {ofe: item['areas'][0] for ofe, item in groups.items()}
area = sum(areas.values())
annual = {ofe: item['annual'] for ofe, item in groups.items()}
weighted = lambda key: sum(annual[ofe][key] * areas[ofe] for ofe in groups) / area
corrected = dict(P=weighted('P'), ET=sum(weighted(key) for key in ('Ep', 'Es', 'Er')),
                 Dp=weighted('Dp'), Q=annual[2]['Q'], lateral=annual[2]['latqcc'] * areas[2] / area)
corrected['residual_before_storage'] = corrected['P'] - sum(corrected[key] for key in ('ET', 'Dp', 'Q', 'lateral'))
formula_book = openpyxl.load_workbook(args.workbook, read_only=True, data_only=False)
formulas = {cell.coordinate: cell.value for row in formula_book.worksheets[0].iter_rows() for cell in row
            if cell.value is not None and (cell.data_type == 'f' or cell.coordinate in ('E18', 'R30'))}
formula_book.close()
spec = importlib.util.spec_from_file_location('wepp_interchange_rust', args.native)
native = importlib.util.module_from_spec(spec)
spec.loader.exec_module(native)
fixture = dict(wepp_id=[1, 1], ofe_id=[1, 2], water_year=[2000, 2000], sim_day_index=[1, 1],
               Area=[250., 750.], P=[10., 10.], Q=[2., 8.], QOFE=[2., 8.*1000./750.],
               latqcc=[4., 6.], Ep=[1., 4.], Es=[.5, 1.], Er=[.5, 1.], Dp=[4., 8.])
with tempfile.TemporaryDirectory(prefix='mofe-consumer-audit-') as directory:
    source, output = Path(directory)/'H.wat.parquet', Path(directory)/'summary.parquet'
    pq.write_table(pa.table(fixture), source)
    native.hillslope_watbal_to_parquet(str(source), str(output), {1: 31})
    actual = pq.read_table(output).to_pylist()
receipt = dict(workbook=str(args.workbook), workbook_sha256=hashlib.sha256(args.workbook.read_bytes()).hexdigest(),
               sheets=sheets, summary_formulas=formulas, exact_lower_area_fraction=areas[2]/area,
               corrected_workbook=corrected, fixture=fixture, native_actual=actual,
               fixture_expected=dict(P=10., runoff=8., lateral=4.5, ET=5., Dp=7.),
               native_sha256=hashlib.sha256(args.native.read_bytes()).hexdigest(),
               revisions={repo: subprocess.check_output(['git', '-C', repo, 'rev-parse', 'HEAD'], text=True).strip()
                          for repo in ('/workdir/wepppy', '/workdir/wepppyo3', '/workdir/wepp-forest')})
args.output.write_text(json.dumps(receipt, indent=2) + '\n')
print(json.dumps(dict(corrected=corrected, native_actual=actual), indent=2))
