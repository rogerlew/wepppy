"""Read retained native outputs without running models or interchange converters."""
from collections import Counter
from datetime import date
import calendar
import hashlib
import json
import math
from pathlib import Path

import audit_particle_closure_v2 as particles
import audit_pass_completeness_r7 as completeness
import combined_hydraulics_r4 as common
from wepppy.soils.ssurgo.retention import load_source_companion

ROOT = Path('/wc1/runs/ro/roads-parameterization-program-20261103/retention-native-v1')
ART = Path(__file__).resolve().parent
EXPECTED_DECLARATION = '631e70e5ddbe6573bd694c18c900b798d621b4c138fd93ed31f591511425e814'
OUTPUTS = {f'H1.{kind}.dat' for kind in ('loss', 'soil', 'pass', 'plot', 'wat', 'element', 'ebe')}
WAT_FIELDS = ('OFE', 'julian', 'year', 'P', 'RM', 'Q', 'Ep', 'Es', 'Er', 'Dp',
              'UpStrmQ', 'SubRIn', 'latqcc', 'Total-Soil Water', 'frozwt', 'Snow-Water',
              'QOFE', 'Tile', 'Irr', 'Area', 'SoilWaterTotal', 'ProfileDepth',
              'ProfilePorosityCap', 'ProfileFCStore', 'ProfileWPStore')


def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def read(path):
    return json.loads(Path(path).read_text())


def key(row):
    return row['label'], row['arm'], row['mode']


def verify(bindings):
    for name, digest in bindings.items():
        assert Path(name).is_file() and not Path(name).is_symlink() and sha(name) == digest, name


def classify(value, reference):
    assert math.isfinite(value) and value >= 0 and math.isfinite(reference) and reference >= 0
    if reference <= 1:
        return 'small_pass' if value <= max(1, 10 * reference) else 'small_exceedance'
    ratio = value / reference
    return 'meaningful_low' if ratio < .1 else 'meaningful_high' if ratio > 10 else 'meaningful_pass'


def delta(before, after):
    assert len(before) == len(after) == 3
    result = []
    for a, b in zip(before, after, strict=True):
        assert set(a) == set(b)
        result.append({name: b[name] - a[name] for name in a})
    return result


def raw_accounting(folder, row, climate):
    """Native text readers plus unchanged pure accounting predicates; no writes."""
    start, end = (int(climate[k][:4]) for k in ('first', 'last'))
    years = end - start + 1
    dates = {(y, j) for y in range(start, end + 1) for j in range(1, 366 + calendar.isleap(y))}
    water_rows = []
    for line in (folder / 'output/H1.wat.dat').read_text().splitlines():
        fields = line.split()
        if not fields or not fields[0].isdigit():
            continue
        assert len(fields) == len(WAT_FIELDS)
        numbers = list(map(float, fields))
        assert all(math.isfinite(v) and v >= 0 for v in numbers[3:])
        parsed = dict(zip(WAT_FIELDS, numbers, strict=True))
        # Native WAT Y is the actual climate year; ELEMENT/EBE use simulation years.
        for name in ('OFE', 'julian', 'year'):
            assert parsed[name] == int(parsed[name])
            parsed[name] = int(parsed[name])
        water_rows.append(parsed)
    assert len(water_rows) == 3 * climate['days']
    slope = [line for line in (folder / 'runs/p1.slp').read_text().splitlines()
             if line and not line.startswith('#')]
    # Preserve the frozen auditor's distinction: emitted geometry for water;
    # declared unrounded width for sediment/report conversion.
    width = float(slope[2].split()[1])
    areas = [width * float(slope[i].split()[1]) for i in (3, 5, 7)]
    water = common.c.e.a.a.water_budget(water_rows, areas, dates, years)
    unavailable = []
    elements = particles.read_elements((folder / 'output/H1.element.dat').read_text().splitlines()[2:],
                                       start, unavailable=unavailable)
    element_rows = []
    for (ofe, day, month, simyear), fields in elements.items():
        when = date(start + simyear - 1, month, day)
        element_rows.append(dict(OFE=ofe, year=when.year, julian=when.timetuple().tm_yday,
                                 SedLeave=float(fields[23])))
    sediment, days = common.c.e.a.sediment_diagnostics(
        element_rows, row['width_m'], years, row['metrics']['sediment_export_kg_yr'])
    assert set(days) <= dates
    ebe_rows = []
    lines = (folder / 'output/H1.ebe.dat').read_text().splitlines()
    for line in lines[3:]:
        fields = line.split()
        assert len(fields) in (14, 16)
        day, month, simyear = map(int, fields[:3])
        when = date(start + simyear - 1, month, day)
        assert all(math.isfinite(float(value)) for value in fields[3:])
        ebe_rows.append(dict(year=when.year, julian=when.timetuple().tm_yday,
                             **{'Sed.Del': float(fields[12])}))
    ebe = common.c.e.a.a.ebe_check(ebe_rows, days, strict=False)
    audit = dict(sediment=sediment, ebe=ebe, water=water, invalid_water_rows=[],
                 physical_pass=not sediment['negative_fluxes'] and sediment['report_reconciled'] and not ebe['mismatches'])
    assert audit == row['audit'], (row['label'], row['arm'], 'raw accounting differs')
    return audit


def normalized_certificate(value):
    return {k: v for k, v in value.items() if k != 'record'}


def main():
    declaration, rows = read(ROOT / 'declaration.json'), read(ROOT / 'results.json')
    results_hash = sha(ROOT / 'results.json')
    assert sha(ROOT / 'declaration.json') == EXPECTED_DECLARATION
    review, start = read(ROOT / 'execution-review.json'), read(ROOT / 'execution-start.json')
    assert review['passed'] and review['declaration_sha256'] == EXPECTED_DECLARATION
    assert start['declaration_sha256'] == EXPECTED_DECLARATION and start['review_sha256'] == sha(ROOT / 'execution-review.json')
    for bindings in (review['files'], declaration['dependencies'], declaration['preparation_files'], declaration['reference_files']):
        verify(bindings)
    assert sha(Path(declaration['scratch']) / 'bin/r7') == declaration['binary_sha256']
    prepared = Path(declaration['preparation_root'])
    assert sha(prepared / 'preparation-result.json') == declaration['preparation_result_sha256']
    prep_declaration = read(prepared / 'declaration.json')
    tasks = {key(t): t for t in declaration['tasks']}
    results = {key(r): r for r in rows}
    expected = {(label, arm, mode) for label in ('B2', 'B3', 'B4', 'B5')
                for arm in ('default', 'optional') for mode in ('ordinary', 'observed')}
    assert len(rows) == len(tasks) == len(results) == 16 and results.keys() == tasks.keys() == expected
    manifest = read(common.c.BATCH / 'inputs/manifest.json')['climates']
    ordinary, output_hashes, certificates, traces = {}, {}, {}, {}
    for identity, row in sorted(results.items()):
        task = tasks[identity]
        assert all(row[name] == value for name, value in task.items())
        folder = Path(row['retained_folder'])
        assert folder == ROOT / 'cases' / row['mode'] / row['arm'] / row['label']
        assert row['execution_folder'] == task['folder'] and row['returncode'] == 0 and row['completed']
        assert read(folder / 'retention-receipt.json') == row
        for section, directory in [('inputs', 'runs'), ('auxiliary_inputs', 'runs'),
                                   ('outputs', 'output'), ('execution_logs', 'runs')]:
            for name, digest in row[section].items():
                assert sha(folder / directory / name) == digest
                assert sha(Path(task['folder']) / directory / name) == digest
        for name, digest in task['staged_files'].items():
            assert sha(folder / name) == sha(Path(task['folder']) / name) == digest
        assert set(row['outputs']) == OUTPUTS
        output_hashes['/'.join(identity)] = row['outputs']
        stdout = (folder / 'runs/stdout').read_text()
        for marker in ('WEPP COMPLETED HILLSLOPE SIMULATION SUCCESSFULLY',
                       'WEPP hourly water seepage update set (UI code)',
                       'Gwcoeff parameters set', 'FAO Penman-Monteith ET Method Implemented'):
            assert marker in stdout
        assert not (folder / 'runs/wepp_observe_frost.on').exists()
        assert (load_source_companion(folder / 'runs/p1.sol', provenance_root=folder) is not None) == (row['arm'] == 'optional')
        if row['mode'] == 'observed':
            normal = results[row['label'], row['arm'], 'ordinary']
            assert row['ordinary_outputs_identical'] and row['outputs'] == normal['outputs']
            assert row['working_directory_expected'] and (folder / 'runs/wepp_observe.on').read_bytes() == b''
            assert {k: v for k, v in row['staged_files'].items() if k != 'runs/wepp_observe.on'} == normal['staged_files']
            trace = folder / 'runs/wepp_observe.log'
            assert sha(trace) == row['trace']['sha256'] and trace.stat().st_size == row['trace']['bytes']
            traces['/'.join(identity)] = dict(row['trace'], interpretation='Hash/retention only; initialized-layer interpretation is independently assigned.')
            continue
        assert row['binary_sha256'] == declaration['binary_sha256']
        assert all(row[k] for k in ('physical_pass', 'particle_pass', 'pass_completeness'))
        record = read(folder / 'record.json')
        assert all(record[k] == row[k] for k in ('case', 'inputs', 'outputs', 'metrics', 'audit', 'binary_sha256'))
        assert common.c.b.parse_loss(folder / 'output/H1.loss.dat', row['width_m']) == row['metrics']
        audit = raw_accounting(folder, row, manifest[row['case']['climate']])
        fresh_particle = particles.audit(folder / 'record.json')
        fresh_calendar = completeness.audit(folder / 'record.json', manifest[row['case']['climate']])
        for name, fresh in [('particle-audit.json', fresh_particle), ('pass-completeness.json', fresh_calendar)]:
            assert fresh['passed'] is True
            assert normalized_certificate(fresh) == normalized_certificate(read(folder / name))
        certificates['/'.join(identity)] = dict(particle=fresh_particle, calendar=fresh_calendar,
                                                record_sha256=sha(folder / 'record.json'), audit=audit)
        reference_path = Path(row['reference_record'])
        assert sha(reference_path) == row['reference_record_sha256']
        reference = read(reference_path)
        for name, digest in reference['outputs'].items():
            assert sha(reference_path.parent / 'output' / name) == digest
        reference_metrics = common.c.b.parse_loss(reference_path.parent / 'output/H1.loss.dat', row['width_m'])
        assert reference_metrics['sediment_export_kg_yr'] == row['reference_kg_yr']
        value = row['metrics']['sediment_export_kg_yr']
        classification = classify(value, row['reference_kg_yr'])
        assert row['export_kg_yr'] == value and row['within'] == classification.endswith('_pass')
        assert row['meaningful'] == (row['reference_kg_yr'] > 1)
        ordinary[row['label'], row['arm']] = row
        print('Verified', row['label'], row['arm'], classification, flush=True)
    contrasts = {}
    for label in ('B2', 'B3', 'B4', 'B5'):
        baseline, candidate = (ordinary[label, arm] for arm in ('default', 'optional'))
        old_path = Path(prep_declaration['cases'][label]['source_seed_folder']) / 'record.json'
        assert declaration['reference_files'][str(old_path)] == sha(old_path)
        old = read(old_path)
        assert old['case'] == baseline['case'] and old['outputs'] == baseline['prior_outputs']
        assert all(sha(old_path.parent / 'output' / n) == digest for n, digest in old['outputs'].items())
        ref = baseline['reference_kg_yr']
        assert ref == candidate['reference_kg_yr']
        before, after = baseline['export_kg_yr'], candidate['export_kg_yr']
        c_before, c_after = classify(before, ref), classify(after, ref)
        annual = [dict(year=a['year'], default_kg=a['sediment_export_kg'], optional_kg=b['sediment_export_kg'],
                       delta_kg=b['sediment_export_kg']-a['sediment_export_kg'])
                  for a, b in zip(baseline['metrics']['annual_export'], candidate['metrics']['annual_export'], strict=True)]
        assert len(annual) == manifest[baseline['case']['climate']]['years']
        contrasts[label] = dict(case=baseline['case'], reference_kg_yr=ref,
            default_kg_yr=before, optional_kg_yr=after, delta_export_kg_yr=after-before,
            percent_change=100*(after-before)/before if before else None,
            default_class=c_before, optional_class=c_after,
            default_ratio=before/ref if ref else None, optional_ratio=after/ref if ref else None,
            default_log10_ratio=math.log10(before/ref) if before > 0 and ref > 0 else None,
            optional_log10_ratio=math.log10(after/ref) if after > 0 and ref > 0 else None,
            small_load_limit_kg_yr=max(1,10*ref) if ref<=1 else None,
            recovery=not c_before.endswith('_pass') and c_after.endswith('_pass'),
            regression=c_before.endswith('_pass') and not c_after.endswith('_pass'),
            paired_changed_outputs=[n for n in sorted(OUTPUTS) if baseline['outputs'][n] != candidate['outputs'][n]],
            annual_export=annual,
            water_ofe_deltas=delta(baseline['audit']['water']['ofes'], candidate['audit']['water']['ofes']),
            sediment_ofe_deltas=delta(baseline['audit']['sediment']['ofes'], candidate['audit']['sediment']['ofes']),
            baseline_water=baseline['audit']['water'], optional_water=candidate['audit']['water'],
            baseline_sediment=baseline['audit']['sediment'], optional_sediment=candidate['audit']['sediment'],
            fresh_default_vs_frozen_r7=dict(frozen_export_kg_yr=old['export_kg_yr'],
                delta_export_kg_yr=before-old['export_kg_yr'],
                changed_outputs=[n for n in sorted(OUTPUTS) if old['outputs'][n] != baseline['outputs'][n]],
                water_ofe_deltas=delta(old['audit']['water']['ofes'], baseline['audit']['water']['ofes']),
                sediment_ofe_deltas=delta(old['audit']['sediment']['ofes'], baseline['audit']['sediment']['ofes'])))
    assert sha(ROOT / 'results.json') == results_hash
    verify(declaration['preparation_files'])
    verify(declaration['reference_files'])
    output = dict(readback_pass=True, scientific_acceptance=False, declaration_sha256=EXPECTED_DECLARATION,
        results_sha256=results_hash, reader_sha256=sha(__file__), acceptance_sha256=sha(ART.parent/'acceptance.md'),
        execution_review_sha256=sha(ROOT/'execution-review.json'),
        checked_native_output_files=112, exact_observer_output_pairs=56,
        ordinary_native_physical_calendar_particle_pass=8, distinct_materials=3,
        selected_seed_counts={arm:dict(Counter(classify(r['export_kg_yr'],r['reference_kg_yr'])
            for (label,a),r in ordinary.items() if a==arm)) for arm in ('default','optional')},
        contrasts=contrasts, audit_readbacks=certificates, output_hashes=output_hashes, observer_trace_hashes=traces,
        native_calls=0, converter_calls=0,
        limits=['Selected four diagnostic cases, not representative 95/90 panel acceptance.',
                'Existing particle criteria cover EVENT payloads; positive non-EVENT sediment dates remain explicit.',
                'Reported soil-stock residual is incomplete water closure; no observed dynamic PERC/ET branch attribution.',
                'Trace hashes/parity are verified here; source-supported initialized-layer mapping is a separate review.',
                'Local scratch execution is not production-mount or complete-controller parity.'])
    destination = ART/'resumption-r7-retention-native-science-readback.json'
    with destination.open('x') as stream:
        json.dump(output,stream,indent=2,sort_keys=True,allow_nan=False)
        stream.write('\n')
    print(json.dumps(dict(readback_pass=True, artifact=str(destination),sha256=sha(destination),
                         results_sha256=results_hash, counts=output['selected_seed_counts'])),flush=True)


if __name__ == '__main__':
    main()
