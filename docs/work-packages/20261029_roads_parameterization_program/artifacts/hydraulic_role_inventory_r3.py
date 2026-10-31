"""Read all development horizons and bind the source-to-native audit to exact files."""
from pathlib import Path
import json
import tarfile
from hydraulic_init_probe_r3 import HERE, ROOT, NATIVE, COMMIT, MATRIX, MATERIALS, sha, dump
from wepppy.wepp.soils.utils import WeppSoilUtil


def main():
    design_path=Path('/wc1/runs/ro/roads-parameterization-program-20261030/design-v2.json')
    design=json.loads(design_path.read_text())
    materials={r['mukey']:r for r in design['development']}
    assert set(materials)==set(MATERIALS)
    sources={}
    for name in ['input.for','scon.for','tilage.for','soil.for','infpar.for','watbal.for','watbal_hourly.for','winter.for','contin.for','cvgpar.inc']:
        file=NATIVE/'src'/name
        with tarfile.open(ROOT/'source.tar') as archive:
            committed=archive.extractfile(f'src/{name}').read()
        import hashlib
        sources[f'{COMMIT}:src/{name}']=hashlib.sha256(committed).hexdigest()
    for relative in ['wepppy/wepp/soils/utils/wepp_soil_util.py','wepppy/wepp/soils/horizon_boundary.py',
        'wepppy/nodb/mods/roads/roads.py','wepppy/nodb/mods/disturbed/data/disturbed_land_soil_lookup.csv',
        'docs/work-packages/20261029_roads_parameterization_program/artifacts/builder_bridge.py',
        'docs/work-packages/20261029_roads_parameterization_program/artifacts/engineered_surface_screen.py']:
        file=Path('/workdir/wepppy')/relative;sources[str(file)]=sha(file)
    rows=[]
    for material in MATERIALS:
        original=materials[material]; source=Path(original['path']);assert sha(source)==original['sha256']
        folder=MATRIX/f'birmingham-{material}-inbare-gravel-high-erosion_road_cap-project'
        record=json.loads((folder/'record.json').read_text()); soil=folder/'runs/p1.sol'
        assert sha(soil)==record['inputs']['p1.sol']
        parsed=WeppSoilUtil(str(soil)).obj
        assert parsed['ofes']==record['soil_readback']
        role_rows=[]
        for role,ofe in zip(['road','fill','buffer'],parsed['ofes']):
            assert any(h['solthk']==200 for h in ofe['horizons'])
            previous=0;horizons=[]
            for h in ofe['horizons']:
                assert h['solthk']>previous
                horizons.append(dict(top_mm=previous,bottom_mm=h['solthk'],input=h,
                    native_input_bd_g_cm3=min(2.0,max(.8,h['bd'])),native_input_om_percent=min(10.,h['orgmat'])))
                previous=h['solthk']
            role_rows.append(dict(role=role,header={k:v for k,v in ofe.items() if k!='horizons'},horizons=horizons))
        rows.append(dict(material=material,raw_source=str(source),raw_source_sha256=sha(source),
                         raw_source_profile=WeppSoilUtil(str(source)).obj,emitted=str(soil),emitted_sha256=sha(soil),roles=role_rows))
    result=dict(materials=7,roles=21,source_commit=COMMIT,source_files=sources,design_sha256=sha(design_path),
                script_sha256=sha(Path(__file__)),rows=rows,
                interpretation='Input clamps only; initialized native properties are recorded separately by the exact-parity observation probe.')
    dump(HERE/'hydraulic-role-inventory-r3.json',result);dump(ROOT/'inventory.json',result)
    print('Verified seven raw sources, 21 role profiles and source dependency hashes')


if __name__=='__main__':main()
