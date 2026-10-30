"""Replay immutable split/unsplit sources through current generated serialization."""
from pathlib import Path
import hashlib
import importlib.util
import json
import shutil
import subprocess

from wepppy.wepp.soils.utils import WeppSoilUtil
from wepppy.nodb.core.wepp import prep_soil

REPO = Path(__file__).resolve().parents[4]
ROOT = Path('/wc1/runs/so/soil-boundary-consistency-20261029-v4')
SOURCE = REPO / 'docs/work-packages/20261029_roads_prepared_soil_hydraulics/artifacts/reproducer'
BINARY = REPO / 'wepp_runner/bin/wepp_261026'
EXPECTED_BINARY = 'a6351d371030f702be5eb0d727d8e7181eeb9d60e9ddf6ce05d9616e5d759d48'


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    assert digest(BINARY) == EXPECTED_BINARY
    ROOT.mkdir(exist_ok=False)
    parser_path = REPO / 'docs/work-packages/20261029_roads_soil_benchmark/artifacts/benchmark.py'
    spec = importlib.util.spec_from_file_location('benchmark_parser', parser_path)
    parser = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(parser)
    evidence = {'binary_sha256': digest(BINARY), 'cases': [],
        'source_sha256': {str(p.relative_to(REPO)): digest(p) for p in [
            Path(__file__), parser_path,
            REPO / 'wepppy/wepp/soils/horizon_boundary.py',
            REPO / 'wepppy/wepp/soils/utils/wepp_soil_util.py',
            REPO / 'wepppy/nodb/core/wepp.py']}}
    for name in ('unsplit', 'split'):
        source = SOURCE / name / 'runs'
        original_hashes = {p.name: digest(p) for p in source.iterdir() if p.is_file()}
        case = ROOT / name
        runs = case / 'wepp/runs'
        runs.mkdir(parents=True)
        output = case / 'wepp/output'
        output.mkdir()
        for path in source.iterdir():
            if path.is_file():
                shutil.copyfile(path, runs / path.name)
        # Ordinary (non-Disturbed) writer, followed by the real hillslope preparation path.
        generated = case / 'generated.sol'
        WeppSoilUtil(str(source / 'p1.sol')).write(str(generated))
        prep_soil(('101', str(generated), str(runs / 'p1.sol'), None, None,
                   0.75, False, 1000, False, 1000, False))
        soil = WeppSoilUtil(str(runs / 'p1.sol'))
        assert all([h['solthk'] for h in o['horizons']] == [150, 200, 400]
                   for o in soil.obj['ofes'])
        for ofe in soil.obj['ofes']:
            upper, lower = ofe['horizons'][1:]
            assert {k:v for k,v in upper.items() if k != 'solthk'} == {
                k:v for k,v in lower.items() if k != 'solthk'}
        with (runs / 'p1.run').open('rb') as stdin, (case / 'native.log').open('wb') as stdout:
            subprocess.run([str(BINARY)], cwd=runs, stdin=stdin, stdout=stdout,
                           stderr=subprocess.STDOUT, check=True, timeout=300)
        assert 'SUCCESSFUL' in (case / 'native.log').read_text().upper()
        result = parser.parse_loss(output / 'H1.loss.dat', width=43.1052293811319)
        assert result['years'] == 16
        wat_rows = parser.validate_wat(output / 'H1.wat.dat',
            {'first': '2000-01-01', 'last': '2015-12-31', 'years': 16})
        assert original_hashes == {p.name: digest(p) for p in source.iterdir() if p.is_file()}
        evidence['cases'].append({'name': name, 'metrics': result, 'validated_wat_rows': wat_rows,
            'source_sha256': original_hashes,
            'input_sha256': {p.name:digest(p) for p in runs.iterdir() if p.is_file()},
            'output_sha256': {p.name:digest(p) for p in output.iterdir() if p.is_file()}})
    assert evidence['cases'][0]['metrics'] == evidence['cases'][1]['metrics']
    def model_records(name):
        return [line for line in (ROOT / name / 'wepp/runs/p1.sol').read_text().splitlines()
                if line.strip() and not line.startswith('#')]
    assert model_records('unsplit') == model_records('split')
    (ROOT / 'evidence.json').write_text(json.dumps(evidence, indent=2) + '\n')
    print(json.dumps({'root': str(ROOT), 'metrics': evidence['cases'][0]['metrics']}, indent=2))


if __name__ == '__main__':
    main()
