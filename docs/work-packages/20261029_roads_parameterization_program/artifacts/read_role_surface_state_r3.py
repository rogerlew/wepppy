"""Read unchanged generated surface inputs and initial native soil output."""
from pathlib import Path
import hashlib
import json

HERE = Path(__file__).resolve().parent
MATRIX = Path('/workdir/wepppy/out/roads-native-funding-20261031/r3-matrix840/matrix-v1')
MATERIALS = ('1718465', '2711184', '2711250', '1718510', '1856573', '53949', '1718494')


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    rows = []
    for material in MATERIALS:
        name = '-'.join(('birmingham', material, 'inbare', 'gravel', 'high', 'erosion_road_cap', 'project'))
        folder = MATRIX / name; record = json.loads((folder / 'record.json').read_text())
        path = folder / 'output/H1.soil.dat'; assert sha(path) == record['outputs'][path.name]
        assert sha(folder / 'runs/p1.sol') == record['inputs']['p1.sol']
        initial = {}
        for line in path.read_text().splitlines():
            values = line.split()
            if values and values[0].isdigit() and values[1:3] == ['1', '1']:
                assert int(values[0]) not in initial
                initial[int(values[0])] = dict(porosity_percent=float(values[3]), effective_conductivity_mm_h=float(values[4]),
                                               suction_mm=float(values[5]), field_capacity=float(values[6]), wilting_point=float(values[7]))
        assert set(initial) == {1, 2, 3}
        rows.append(dict(material=material, case=record['case'], record_sha256=sha(folder / 'record.json'),
                         soil_output_sha256=sha(path),
                         roles={role: dict(input_surface_horizon=record['soil_readback'][i]['horizons'][0],
                                           ksatadj=record['soil_readback'][i].get('ksatadj'),
                                           initial_reported_state=initial[i + 1]) for i, role in enumerate(('road', 'fill', 'buffer'))}))
    result = dict(scope='One fixed Birmingham/inbare/gravel/high case for each of seven development materials; emitted surface horizon and day1/year1 native state. Diagnostic state, not a compaction or causal validation.',
                  source='Final revision3 matrix', script_sha256=sha(Path(__file__)), rows=rows)
    (HERE / 'generated-role-surface-state-r3.json').write_text(json.dumps(result, indent=2) + '\n')
    print('Seven material surface-state readbacks verified')


if __name__ == '__main__':
    main()
