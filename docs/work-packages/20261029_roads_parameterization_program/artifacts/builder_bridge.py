"""Read back actual production configurations with isolated generated-soil injection."""
from copy import deepcopy
import itertools
import json
from pathlib import Path
import shutil

import continuation as c
b = c.b
ROOT = c.ROOT / 'builder-bridge-v2'
TEXTURES = {'1718465':'sand','2711184':'loam','2711250':'silt','1718510':'clay',
            '1856573':'loam','53949':'loam','1718494':'loam'}


def roles(source, directory):
    from wepppy.wepp.soils.utils import WeppSoilUtil, simple_texture
    from wepppy.nodb.mods.disturbed.disturbed import read_disturbed_land_soil_lookup
    from wepppy.nodb.core.wepp import prep_soil
    directory.mkdir(parents=True)
    soil = WeppSoilUtil(str(source))
    texture = simple_texture(clay=soil.clay, sand=soil.sand)
    lookup = read_disturbed_land_soil_lookup('/workdir/wepppy/wepppy/nodb/mods/disturbed/data/disturbed_land_soil_lookup.csv')
    result = {}
    for role in ('bare', 'forest'):
        conditioned, prepared = directory/f'{role}-conditioned.sol', directory/f'{role}.sol'
        soil.to_over9000(lookup[(texture,role)].copy(), version=9002).write(str(conditioned))
        prep_soil((directory.name,str(conditioned),str(prepared),None,None,.75,False,700,False,None))
        result[role] = WeppSoilUtil(str(prepared))
        if 200 not in [h['solthk'] for h in result[role].obj['ofes'][0]['horizons']]:
            raise ValueError('Missing normalized 200 mm boundary')
    return texture, result


def inject(path, prepared, order):
    from wepppy.wepp.soils.utils import WeppSoilUtil
    reference = WeppSoilUtil(str(path))
    original = deepcopy(reference.obj['ofes'])
    soil = deepcopy(prepared['bare'])
    before = [deepcopy(prepared['forest' if role==3 else 'bare'].obj['ofes'][0]) for role in order]
    result = deepcopy(before)
    road_index = order.index(1)
    road, legacy = result[road_index], original[road_index]
    for field in ('ki','kr','shcrit'):
        road[field] = legacy[field]
    road['ksatadj'] = '0'
    cap = float(legacy['avke'])
    for h in road['horizons']:
        if h['solthk'] <= 200:
            h['ksat'] = min(h['ksat'],cap)
    soil.obj['ofes'] = result
    soil.obj['ntemp'] = len(order)
    soil.write(str(path))
    actual = WeppSoilUtil(str(path)).obj['ofes']
    if actual != result:
        raise ValueError('Generated road transformation readback drift')
    restored = deepcopy(actual)
    for field in ('ki','kr','shcrit','ksatadj'):
        restored[road_index][field] = before[road_index][field]
    for h, old in zip(restored[road_index]['horizons'],before[road_index]['horizons']):
        if h['solthk'] <= 200:
            h['ksat'] = old['ksat']
    if restored != before:
        raise ValueError('Undeclared role/material mutation')
    return dict(order=order, road_index=road_index, cap_mm_h=cap,
                generated_before=before, generated_after=actual, legacy=original)


def main():
    from tests.roads.roads_matrix import Case, ARRANGEMENTS, initialize, prepare
    from wepppy.nodb.mods.roads import Roads
    ROOT.mkdir(exist_ok=False)
    initialize(ROOT)
    roads = Roads(str(ROOT),'disturbed9002-wbt-mofe.cfg')
    design = json.loads((c.ROOT/'design-v2.json').read_text())
    declared = list(itertools.product([r['mukey'] for r in design['development']],ARRANGEMENTS,('gravel','paved'),('high','low','none')))
    b.dump(ROOT/'declaration.json',dict(cases=declared,reference_texture_by_material=TEXTURES,texture_note='Declared legacy comparison classes retained from earlier studies; generated preparation uses its own detailed texture.',script_sha256=b.digest(__file__),
        limits='Builder/readback only; candidate injection isolated from production. Native validation and configuration approval remain separate gates.'))
    shutil.copy2(__file__,ROOT/'executed-builder-bridge.py')
    results=[]
    for material in design['development']:
        if b.digest(material['path']) != material['sha256']:
            raise ValueError('Material drift')
        texture, prepared = roles(material['path'],ROOT/'prepared'/material['mukey'])
        for arrangement,surface,traffic in itertools.product(ARRANGEMENTS,('gravel','paved'),('high','low','none')):
            identifier=len(results)+1
            case=Case('median',TEXTURES[material['mukey']],surface,traffic,arrangement)
            record=prepare(roads,ROOT,case,identifier)
            path=ROOT/f'wepp/roads/runs/p{identifier}.sol'
            shutil.copy2(path,path.with_suffix('.legacy.sol'))
            record['generated_readback']=inject(path,prepared,record['ofe_order'])
            record['material']=material
            record['candidate_soil_sha256']=b.digest(path)
            b.dump(ROOT/f'case-{identifier}.json',record)
            results.append(dict(identifier=identifier,material=material['mukey'],case=record['case'],
                                road_index=record['generated_readback']['road_index'],record_sha256=b.digest(ROOT/f'case-{identifier}.json')))
        print(material['mukey'],len(results),'readback cases',flush=True)
    b.dump(ROOT/'results.json',results)
    summary=dict(cases=len(results),materials=7,arrangements=7,surfaces=2,traffic_levels=3,
                 all_readback_pass=True,production_changes=False,native_validation=False)
    b.dump(c.HERE/'builder-bridge-v2-summary.json',summary)
    print(json.dumps(summary,indent=2))


if __name__ == '__main__':
    main()
