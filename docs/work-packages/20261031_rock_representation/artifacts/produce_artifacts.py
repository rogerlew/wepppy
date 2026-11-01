"""Generate and independently read real local artifacts for the two repairs."""
import argparse
import hashlib
import json
import runpy
from pathlib import Path
import numpy as np
from wepppy.locales.earth.soils.isric import ISRICSoilData
from wepppy.nodb.mods.rusle.c_integration import run_rusle_c_factor


def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--out',type=Path,required=True)
    a=ap.parse_args();a.out.mkdir(parents=True,exist_ok=False)
    repo=Path.cwd()
    soil_helpers=runpy.run_path(str(repo/'tests/locales/earth/soils/test_isric_rock_basis.py'))
    c_helpers=runpy.run_path(str(repo/'tests/nodb/mods/test_rusle_c_integration.py'))
    soil_root=a.out/'soil';soil_helpers['write_soilgrids_fixture'](soil_root)
    soil=ISRICSoilData(str(soil_root));soil.wgs_bbox=(0,0,2,2)
    key,summary,_=soil.build_soil(.5,.5,soil_fn='rock.sol')
    assert key and summary
    rows=[]
    for line in (soil_root/'rock.sol').read_text().splitlines():
        if not line.startswith('#') and len(line.split())==11:rows.append(list(map(float,line.split())))
    assert [r[0] for r in rows]==[50,150,200,300,600,1000,2000]
    assert all(r[-1]==33.8 and r[1]==1.3 for r in rows)
    receipts=[]
    for mode in ['observed_rap','scenario_sbs']:
        for path in ['soils/cfvo_0-5cm_Q0.5.tif','polaris/cfvo_mean_0_5.tif']:
            for raw in [20,100,101,800]:
                root=a.out/f'{mode}-{Path(path).parent}-{raw}';root.mkdir()
                dem=root/'dem.tif';c_helpers['_write_raster'](dem,np.ones((1,2)),dtype='float32',nodata=-9999)
                cfvo=root/path;cfvo.parent.mkdir()
                c_helpers['_write_raster'](cfvo,np.array([[raw,-9999]]),dtype='float32',nodata=-9999)
                kwargs={}
                if mode=='observed_rap':
                    rap=root/'rap.tif';c_helpers['_write_default_rap_dataset'](rap,bare_ground=np.array([[50,50]]))
                    kwargs['rap']=str(rap);bare=.5;control='rock_fraction_of_rap_bare'
                else:
                    landuse=root/'landuse.tif';mapping=root/'disturbed.json'
                    c_helpers['_write_raster'](landuse,np.array([[52,52]]),dtype='uint8',nodata=0)
                    c_helpers['_write_disturbed_mapping'](mapping,{52:{'DisturbedClass':'shrub'}})
                    kwargs.update(landuse=str(landuse),disturbed_mapping_path=str(mapping));bare=.1;control='rock_fraction_of_sbs_bare'
                result=run_rusle_c_factor(str(root),str(dem),c_mode=mode,**kwargs)
                manifest=json.loads(Path(result.manifest).read_text());report=manifest['c'][control]
                assert abs(report['surface_rock_cover_proxy_0_1']-raw/1000)<1e-14
                assert report['sources']['cfvo']['scale_divisor']==10
                raster,nodata=c_helpers['_read_single_band'](result.c)
                expected=np.exp(-.04*100*(1-bare*(1-min(raw/1000/bare,1))))
                assert np.allclose(raster,expected) and np.all(raster!=nodata)
                receipts.append(dict(mode=mode,source=path,raw_cfvo=raw,proxy=report['surface_rock_cover_proxy_0_1'],c_expected=float(expected),c_values=raster.tolist()))
    bindings={str(p.relative_to(repo)):sha(p) for p in [repo/'wepppy/locales/earth/soils/isric/__init__.py',repo/'wepppy/wepp/soils/rock_fragments.py',repo/'wepppy/nodb/mods/rusle/c_integration.py',repo/'tests/locales/earth/soils/test_isric_rock_basis.py',repo/'tests/nodb/mods/test_rusle_c_integration.py']}
    result=dict(passed=True,soil_horizons=rows,soil_source_volume_percent=20,soil_source_density=1.3,cases=receipts,bindings=bindings,files={str(p.relative_to(a.out)):sha(p) for p in sorted(a.out.rglob('*')) if p.is_file()})
    (a.out/'receipt.json').write_text(json.dumps(result,indent=2)+'\n')
    print('PASS: real SoilGrids extraction/build,7 emitted horizons,16 C raster/manifest cases')


if __name__=='__main__':main()
