"""Forest-only isolated project acceptance; never mutate the source project."""
import json
import logging
import os
from pathlib import Path
import time
from types import SimpleNamespace

from osgeo import gdal

from wepppy.rq.project_rq_fork import prepare_fork_run
from wepppy.nodb.core import Ron, Landuse, Soils, Wepp, Climate
from wepppy.nodb.mods.disturbed import Disturbed
from wepppy.nodb.core.climate_build_helpers import _retrieve_prism_revision_tiles
from wepppy.all_your_base.geo.webclients.wmesque import wmesque_retrieve
from wepp_runner.wepp_runner import run_hillslope

def main():
    source=Path('/wc1/runs/an/anisotropic-sassafras')
    runid='wmesque-acceptance-'+str(int(time.time()))
    destination=Path('/wc1/runs/wm')/runid
    evidence={'source':str(source),'destination':str(destination),'checks':[]}
    print(json.dumps(evidence),flush=True)
    prepare_fork_run('anisotropic-sassafras',runid,undisturbify=False,
        skip_wepp_runs_output=True,skip_omni_scenarios_contrasts=True,status_channel='wmesque-acceptance',
        publish_status=lambda channel,message: print(message,flush=True),
        get_wd=lambda _:str(source),get_primary_wd=lambda _:str(destination),
        wait_for_paths=lambda paths,**kwargs: None,ron_cls=Ron,disturbed_cls=Disturbed,
        landuse_cls=Landuse,soils_cls=Soils,initialize_ttl=None)
    try:
        ron=Ron.getInstance(str(destination));landuse=Landuse.getInstance(str(destination))
        soils=Soils.getInstance(str(destination));wepp=Wepp.getInstance(str(destination))
        assert all(Path(obj.wd)==destination for obj in (ron,landuse,soils,wepp))
        wepp.wepp_bin = 'wepp_261010'
        evidence['wepp_bin'] = wepp.wepp_bin
        # Exercise deployment priority with shared forest service, then the unchanged master.
        os.environ['WMESQUE_ENDPOINTS']=json.dumps(['http://wmesque2:8030','https://wepp.cloud/webservices/wmesque2'])
        ron.fetch_dem();evidence['checks'].append('Ron.fetch_dem actual acquisition')
        landuse.build();evidence['checks'].append('Landuse.build actual acquisition and summaries')
        # Preserve existing model inputs while directly testing the requested SSURGO source.
        soil_tile=destination/'soils'/'wmesque-acceptance.tif'
        wmesque_retrieve(soils.ssurgo_db,ron.map.extent,str(soil_tile),ron.map.cellsize)
        evidence['checks'].append('actual SSURGO acquisition')
        normals=destination/'climate'/'wmesque-acceptance';normals.mkdir(exist_ok=True)
        climate=SimpleNamespace(wmesque_version=2,wmesque_endpoint=None,logger=logging.getLogger('acceptance'))
        _retrieve_prism_revision_tiles(climate,ron.map,*[str(normals/(name+'.tif')) for name in ('ppt','tmin','tmax')])
        evidence['checks'].append('actual climate helper PRISM acquisitions')
        wepp.prep_hillslopes(max_workers=1)
        inputs=Path(wepp.runs_dir)
        hill=next(inputs.glob('p*.slp')).stem[1:]
        evidence['prepared_inputs']={ext:(inputs/f'p{hill}.{ext}').stat().st_size for ext in ('slp','sol','man','cli','run')}
        assert all(evidence['prepared_inputs'].values())
        evidence['checks'].append('fresh prepared hillslope inputs')
        result=run_hillslope(hill,str(inputs),wepp_bin=wepp.wepp_bin,timeout=120,timeout_retries=0)
        assert result[0] is True, result
        evidence['execution']=list(result)
        evidence['checks'].append('fresh WEPP hillslope execution')
        for label,path in [('dem',Path(ron.dem_fn)),('landuse',Path(landuse.lc_fn)),('soils',soil_tile)]+[(name,normals/(name+'.tif')) for name in ('ppt','tmin','tmax')]:
            ds=gdal.Open(str(path));assert ds is not None
            metadata=json.loads(Path(str(path)+'.meta').read_text())
            evidence[label]={'path':str(path),'shape':[ds.RasterYSize,ds.RasterXSize],'bands':ds.RasterCount,
                             'range':ds.GetRasterBand(1).ComputeRasterMinMax(),
                             'endpoint':metadata['wmesque_retrieve']['wmesque_endpoint']}
    finally:
        (destination/'wmesque-acceptance.json').write_text(json.dumps(evidence,indent=2))
    print(json.dumps(evidence,indent=2))


if __name__ == '__main__':
    main()
