"""Independently join final assignments/soil texture to serialized year crop keys."""
from pathlib import Path
import hashlib
import json
from wepppy.nodb.core import Landuse, Watershed
from wepppy.nodb.mods.disturbed import Disturbed
from wepppy.nodb.mods.disturbed.disturbed import lookup_disturbed_class
from wepppy.wepp.management import read_management
from wepppy.wepp.soils.utils import WeppSoilUtil, simple_texture
import wepppyo3.wepp_interchange.wepp_interchange_rust as installed_rust

def main():
    root = Path('/wc1/runs/mi/mipa-awake-20261102')
    evidence = Path('/workdir/wepppy/docs/work-packages/20261102_mofe_input_producer_audit/artifacts')
    landuse = Landuse.getInstance(str(root))
    translator = Watershed.getInstance(str(root)).translator_factory()
    lookup = Disturbed.getInstance(str(root)).land_soil_replacements_d
    runs = root / 'wepp/runs'
    rows = {parts[0]: tuple(map(float, parts[1:3])) for parts in
            (line.split(',') for line in (runs / 'pmetpara.txt').read_text().splitlines()[1:])}
    checks = []
    for top, assignments in landuse.domlc_mofe_d.items():
        stem = f'p{translator.wepp(top=int(top))}'
        man = read_management(str(runs / (stem + '.man')))
        soil = WeppSoilUtil(str(runs / (stem + '.sol')))
        years = {year.name: year for year in man.years}
        for index, ofe in enumerate(soil.obj['ofes']):
            label = landuse.managements[assignments[str(index + 1)]].disturbed_class
            normalized = lookup_disturbed_class(label)
            if normalized == label and label and 'mulch' in label:
                normalized = 'mulch'
            elif normalized == label and label and 'thinning' in label:
                normalized = 'thinning'
            texture = simple_texture(clay=ofe['horizons'][0]['clay'], sand=ofe['horizons'][0]['sand'])
            replacement = lookup.get((texture, normalized))
            expected = (0.95, 0.8) if not normalized or 'developed' in normalized or replacement is None else (
                float(replacement['pmet_kcb']), float(replacement['pmet_rawp']))
            crops = sorted({years[ref.loop_name].data.itype.loop_name
                            for rotation in man.man.loops for year in rotation.years
                            for ref in year[index].manindx})
            assert crops
            assert all(rows[crop] == expected for crop in crops), (top, index, crops, expected)
            checks.append({'topaz': top, 'ofe': index + 1, 'class': label, 'texture': texture,
                           'crop_keys': crops, 'expected': expected})
    repo = Path('/workdir/wepppy')
    sources = ['wepppy/wepp/management/managements.py', 'wepppy/wepp/management/pmetpara.py',
               'wepppy/wepp/management/utils/multi_ofe.py', 'wepppy/nodb/core/wepp.py',
               'wepppy/nodb/mods/disturbed/disturbed.py', 'wepppy/wepp/soils/utils/wepp_soil_util.py']
    result = {'checks': checks, 'table_rows': len(rows), 'distinct_pairs': sorted(set(rows.values())),
              'source_sha256': {name: hashlib.sha256((repo / name).read_bytes()).hexdigest() for name in sources},
              'installed_rust': {'path': installed_rust.__file__, 'sha256': hashlib.sha256(Path(installed_rust.__file__).read_bytes()).hexdigest()},
              'scope': 'Serialized producer/year-reference lookup only; native execution remains HOLD'}
    (evidence / 'actual_project_coefficients_v3.json').write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps({'elements_checked': len(checks), 'table_rows': len(rows), 'distinct_pairs': result['distinct_pairs']}))


if __name__ == "__main__":
    main()
