"""Reproduce local actual-binary synthetic and authentic incomplete M1 bundles.

Run through wctl exec weppcloud python; output directory must not exist.
"""
import argparse
from dataclasses import replace
import json
import os
import shutil
from xml.etree import ElementTree as ET
from pathlib import Path

import numpy as np
import rasterio
from rasterio.transform import from_origin

from wepppy.nodb.mods.postfire_debris_flow.dnbr import normalize_dnbr
from wepppy.nodb.mods.postfire_debris_flow.integration import M1Error, M1Inputs, build_m1_predictors, evaluate_m1_scenarios
from wepppy.nodb.mods.postfire_debris_flow.m1_inputs import digest


def write_raster(path, values, *, nodata=-9999):
    with rasterio.open(path, 'w', driver='GTiff', height=values.shape[0], width=values.shape[1],
                       count=1, dtype=values.dtype, nodata=nodata, crs='EPSG:32611',
                       transform=from_origin(500000, 4000000, 30, 30)) as dst:
        dst.write(values, 1)


def identity(inputs):
    paths = [inputs.dem, inputs.mask, inputs.outlet, inputs.sbs, inputs.k, inputs.k_manifest,
             inputs.dnbr, inputs.dnbr_manifest, *inputs.lineage_sources]
    return replace(inputs, expected_sha256={str(p): digest(p) for p in paths if p is not None})


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output', type=Path)
    parser.add_argument('--binary', type=Path, default=Path('/workdir/weppcloud-wbt/target/release/whitebox_tools'))
    args = parser.parse_args()
    output = args.output.absolute()
    output.mkdir(mode=0o700)
    source = output/'synthetic-sources'; source.mkdir()
    dem = np.tile(np.arange(7, dtype='float64')*30, (7, 1))
    mask = np.zeros((7,7),dtype='int16');mask[1:-1,1:-1]=1
    write_raster(source/'dem.tif', dem)
    write_raster(source/'mask.tif', mask)
    write_raster(source/'sbs.tif', np.full((7,7),3,dtype='int16'),nodata=255)
    write_raster(source/'k_polaris_nomograph.tif', np.full((7,7),.3))
    write_raster(source/'raw-dnbr.tif', np.full((7,7),400,dtype='int16'))
    (source/'outlet.geojson').write_text(json.dumps({'type':'Point','coordinates':[500045,3999955]}))
    mode = {'vfs_source':'rusle2_estimated_from_sand','structure_class_mapping':'modeled_texture_proxy_v1',
            'permeability_class_mapping':'modeled_ksat_proxy_v1','cfvo_profile_fragment_adjustment':{'status':'not_applied'}}
    k = {'selected_modes':['polaris_nomograph'],'artifacts':{'nomograph':'rusle/k_polaris_nomograph.tif'},
         'statistic':'mean','near_surface_depths':['0_5','5_15'],'near_surface_weights_cm':{'0_5':5.,'5_15':10.},
         'gap_fill_policy':{'enabled':False},'gap_fill_summary':{'synthetic_no_fill':True},
         'mode_contract':{'polaris_nomograph':mode}}
    (source/'manifest.json').write_text(json.dumps({'k':k}))
    normalize_dnbr(source/'raw-dnbr.tif',source/'dem.tif',source/'mask.tif',source/'normalized',scale_factor=.001)
    inputs = identity(M1Inputs(dem=source/'dem.tif',mask=source/'mask.tif',outlet=source/'outlet.geojson',
                      sbs=source/'sbs.tif',k=source/'k_polaris_nomograph.tif',k_manifest=source/'manifest.json',
                      dnbr=source/'normalized/dnbr.tif',dnbr_manifest=source/'normalized/manifest.json',
                      lineage_sources=(source/'raw-dnbr.tif',),expected_sha256={},
                      wbt_sha256=digest(args.binary),source_kind='synthetic'))
    synthetic=build_m1_predictors(inputs,output/'synthetic-complete',wbt_executable=args.binary)
    root=Path('/wc1/runs/st/strained-mod')
    # Materialize statistics-only PAM companions outside the project. The local
    # adapter intentionally rejects auxiliary metadata rather than ignoring it.
    copies=output/'real-sources';copies.mkdir()
    original_hashes={}
    for relative in ('dem/dem.tif','dem/wbt/bound.tif','dem/wbt/outlet.geojson',
                     'disturbed/sbs_4class.tif','rusle/k_polaris_nomograph.tif','rusle/manifest.json'):
        original=root/relative
        copy=copies/relative;copy.parent.mkdir(parents=True,exist_ok=True)
        original_hashes[str(original)]=digest(original)
        auxiliary=Path(str(original)+'.aux.xml')
        if auxiliary.exists():
            original_hashes[str(auxiliary)]=digest(auxiliary)
            tree=ET.fromstring(auxiliary.read_text())
            assert all(node.tag in ('PAMDataset','PAMRasterBand','Metadata','MDI') for node in tree.iter())
            assert all(node.attrib.get('key','').startswith('STATISTICS_') for node in tree.iter('MDI'))
        shutil.copyfile(original,copy)
        if original.suffix == '.tif':
            with rasterio.open(original) as a,rasterio.open(copy) as b:
                assert a.crs == b.crs and a.transform == b.transform and a.shape == b.shape
                assert np.array_equal(a.read_masks(1),b.read_masks(1))
                valid=a.read_masks(1)>0
                assert np.array_equal(a.read(1)[valid],b.read(1)[valid])
    root=copies
    real_inputs=identity(M1Inputs(dem=root/'dem/dem.tif',mask=root/'dem/wbt/bound.tif',
                        outlet=root/'dem/wbt/outlet.geojson',sbs=root/'disturbed/sbs_4class.tif',
                        k=root/'rusle/k_polaris_nomograph.tif',k_manifest=root/'rusle/manifest.json',
                        expected_sha256={},wbt_sha256=digest(args.binary),source_kind='real',sbs_alignment='nearest'))
    real=build_m1_predictors(real_inputs,output/'real-missing-dnbr',wbt_executable=args.binary)
    # Explicitly labeled process-failure fixture; never alter the real executable.
    failing=output/'controlled-failing-tool'
    failing.write_text('#!/bin/sh\nexit 7\n');failing.chmod(0o700)
    try:
        build_m1_predictors(replace(inputs,wbt_sha256=digest(failing)),output/'controlled-tool-failure',wbt_executable=failing)
    except M1Error as exc:
        assert exc.code == 'tool_failed'
    else:
        raise AssertionError('Controlled executable failure was not preserved')
    assert (output/'controlled-tool-failure/incomplete.json').exists()
    assert not (output/'controlled-tool-failure/manifest.json').exists()
    assert all(digest(p)==h for p,h in original_hashes.items())
    report={'original_project_sha256':original_hashes, 'preparation':'Byte-identical copied TIFFs; statistics-only PAM excluded after explicit XML and raster identity checks', 'output':str(output),'binary':str(args.binary),'binary_sha256':digest(args.binary),
            'identity':{'uid':os.getuid(),'gid':os.getgid(),'groups':os.getgroups()},
            'synthetic':{'availability':synthetic['availability'],'predictors':synthetic['predictors'],
                         'scenarios':evaluate_m1_scenarios(synthetic,[(15,10),(30,20),(60,30)])},
            'real':{'availability':real['availability'],'predictors':real['predictors'],
                    'scenarios':evaluate_m1_scenarios(real,[(15,10),(30,20),(60,30)])},
            'limitation':'No authentic normalized dNBR overlaps inventoried K projects; complete real T/F/S gate remains open.'}
    (output/'evidence.json').write_text(json.dumps(report,indent=2,allow_nan=False)+'\n')
    print(json.dumps({'output':str(output),'synthetic':synthetic['availability'],'real':real['availability']}))


if __name__ == '__main__':
    main()
