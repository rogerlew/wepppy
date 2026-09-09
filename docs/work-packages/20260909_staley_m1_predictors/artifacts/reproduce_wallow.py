"""Read-only Wallow project M1 acceptance using explicitly matched assessment imagery."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
from xml.etree import ElementTree as ET
import zipfile

import numpy as np
import rasterio

from wepppy.nodb.mods.postfire_debris_flow.dnbr import normalize_dnbr
from wepppy.nodb.mods.postfire_debris_flow.integration import M1Inputs, build_m1_predictors, evaluate_m1_scenarios
from wepppy.nodb.mods.postfire_debris_flow.m1_inputs import digest, prepare, read_raster

ARCHIVE_SHA256 = '423eb8b0edf87a733a1d441d64e11295b6fb65db3c18c30b00bab250998ecaaf'
PREFIX = 'Wallow_FinalSoilBurnSeverity/originalBARC_20110701/'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output',type=Path)
    parser.add_argument('--assessment', choices=('july1', 'final-june23'), default='july1')
    parser.add_argument('--project',type=Path,default=Path('/wc1/runs/wo/woolen-refusal'))
    parser.add_argument('--archive',type=Path,default=Path('/workdir/wepppy/tests/nodb/mods/fixtures/postfire_debris_flow_wallow/.source-cache/Wallow_FinalSoilBurnSeverity.zip'))
    parser.add_argument('--binary',type=Path,default=Path('/workdir/weppcloud-wbt/target/release/whitebox_tools'))
    args=parser.parse_args()
    assert digest(args.archive)==ARCHIVE_SHA256
    output=args.output.absolute();output.mkdir(mode=0o700)
    source=output/'sources';source.mkdir()
    root=args.project
    original_hashes={}
    relatives=('dem/dem.tif','dem/wbt/bound.tif','dem/wbt/outlet.geojson',
               'disturbed/sbs_4class.tif','rusle/k_polaris_nomograph.tif','rusle/manifest.json',
               'soils.nodb','disturbed.nodb','watershed.nodb')
    for relative in relatives:
        original=root/relative;copied=source/relative;copied.parent.mkdir(parents=True,exist_ok=True)
        original_hashes[str(original)]=digest(original)
        auxiliary=Path(str(original)+'.aux.xml')
        if auxiliary.exists():
            original_hashes[str(auxiliary)]=digest(auxiliary)
            tree=ET.fromstring(auxiliary.read_text())
            assert all(n.tag in ('PAMDataset','PAMRasterBand','Metadata','MDI') for n in tree.iter())
            assert all(n.attrib.get('key','').startswith('STATISTICS_') for n in tree.iter('MDI'))
        shutil.copyfile(original,copied)
        if original.suffix=='.tif':
            with rasterio.open(original) as a,rasterio.open(copied) as b:
                assert (a.crs,a.transform,a.shape)==(b.crs,b.transform,b.shape)
                assert np.array_equal(a.read_masks(1),b.read_masks(1))
                valid=a.read_masks(1)>0
                assert np.array_equal(a.read(1)[valid],b.read(1)[valid])
    soils=json.loads((source/'soils.nodb').read_text())['py/state']['soils']
    assert soils
    for entry in soils.values():
        state=entry['py/state'];name=state['fname']
        assert Path(name).name==name
        soil=root/'soils'/name
        assert soil.is_file() and soil.stat().st_size>0
        original_hashes[str(soil)]=digest(soil)
    final = args.assessment == 'final-june23'
    prefix = 'Wallow_FinalSoilBurnSeverity/FinalSoilBurnSeverity/' if final else PREFIX
    upload_name = 'wallow_finalsoilburnseverity.tif' if final else 'wallow_20110701_barc256_alb.img'
    configured = json.loads((source/'disturbed.nodb').read_text())['py/state']['_disturbed_fn']
    assert configured == upload_name, 'Selected assessment does not match current project SBS source'
    uploaded = root/'disturbed'/upload_name
    original_hashes[str(uploaded)] = digest(uploaded)
    dnbr_member = prefix + ('wallow_dnbr.img' if final else 'wallow_20110701_dnbr_alb.img')
    metadata_member = prefix + ('FINAL_ Wallow_20110623_metadata_alb.txt' if final else 'Wallow_20110701_metadata_alb.txt')
    upload_provenance = {}
    with zipfile.ZipFile(args.archive) as archive:
        if final:
            fixture = Path('/workdir/wepppy/tests/nodb/mods/fixtures/postfire_debris_flow_wallow')
            provenance_path = fixture/'wallow_finalsoilburnseverity.manifest.json'
            original_hashes[str(provenance_path)] = digest(provenance_path)
            upload_provenance = json.loads(provenance_path.read_text())
            assert upload_provenance['archive_sha256'] == ARCHIVE_SHA256
            assert digest(uploaded) == upload_provenance['sha256']
            for component in upload_provenance['sources']:
                assert hashlib.sha256(archive.read(component['member'])).hexdigest() == component['sha256']
            with rasterio.open(uploaded) as raw, rasterio.open(source/'disturbed/sbs_4class.tif') as prepared:
                assert (raw.crs, raw.transform, raw.shape) == (prepared.crs, prepared.transform, prepared.shape)
                valid = raw.read_masks(1)>0
                assert np.array_equal(valid, prepared.read_masks(1)>0)
                assert np.array_equal(raw.read(1)[valid]-1, prepared.read(1)[valid])
        else:
            assert hashlib.sha256(archive.read(prefix+uploaded.name)).hexdigest()==digest(uploaded)
        (source/'dnbr.img').write_bytes(archive.read(dnbr_member))
        (source/'source_metadata.txt').write_bytes(archive.read(metadata_member))
    postfire_date = '2011-06-23' if final else '2011-07-01'
    # Materialize the original continuous HFA as a self-contained GeoTIFF;
    # do not infer missing pixels or derive severity from this dNBR.
    with rasterio.open(source/'dnbr.img') as src:
        values=src.read(1);mask=src.read_masks(1)
        with rasterio.Env(GDAL_TIFF_INTERNAL_MASK=True):
            with rasterio.open(source/'raw_dnbr.tif','w',driver='GTiff',height=src.height,width=src.width,
                               count=1,dtype=src.dtypes[0],crs=src.crs,transform=src.transform,
                               nodata=src.nodata,compress='deflate') as dst:
                dst.write(values,1);dst.write_mask(mask)
        with rasterio.open(source/'raw_dnbr.tif') as dst:
            assert (dst.crs,dst.transform,dst.shape)==(src.crs,src.transform,src.shape)
            assert np.array_equal(dst.read(1),values) and np.array_equal(dst.read_masks(1),mask)
    bound,valid,grid=read_raster(source/'dem/wbt/bound.tif',target_grid=True)
    domain=valid&(bound>0)
    prepare(source/'domain.tif',domain.astype(float),np.ones(domain.shape,dtype=bool),grid)
    normalization=normalize_dnbr(source/'raw_dnbr.tif',source/'dem/dem.tif',source/'domain.tif',
                                 output/'normalized',scale_factor=.001,prefire_date='2011-05-30',postfire_date=postfire_date)
    paths={'dem':source/'dem/dem.tif','mask':source/'dem/wbt/bound.tif','outlet':source/'dem/wbt/outlet.geojson',
           'sbs':source/'disturbed/sbs_4class.tif','k':source/'rusle/k_polaris_nomograph.tif',
           'k_manifest':source/'rusle/manifest.json','dnbr':output/'normalized/dnbr.tif',
           'dnbr_manifest':output/'normalized/manifest.json'}
    lineage=(source/'raw_dnbr.tif',source/'domain.tif')
    hashes={str(p):digest(p) for p in (*paths.values(),*lineage)}
    inputs=M1Inputs(**paths,lineage_sources=lineage,expected_sha256=hashes,
                    wbt_sha256=digest(args.binary),source_kind='real',sbs_alignment='nearest')
    bundle=build_m1_predictors(inputs,output/'bundle',wbt_executable=args.binary)
    assert bundle['status']=='complete'
    assert all(digest(p)==h for p,h in original_hashes.items()) and digest(args.archive)==ARCHIVE_SHA256
    scenarios=evaluate_m1_scenarios(bundle,[(15,10),(30,20),(60,30)])
    with rasterio.open(output/'normalized/dnbr.tif') as ds:
        d=ds.read(1);assert np.isfinite(d[domain]).all()
        basin_range=[float(d[domain].min()),float(d[domain].max())]
    report={'project_url':'https://wc.bearhive.duckdns.org/weppcloud/runs/woolen-refusal/disturbed9002_wbt/',
            'project':str(root),'output':str(output),'source_kind':'real','assessment':postfire_date + (' final polygon severity, matching rebuilt run SBS' if final else ' original BARC, matching run SBS'),
            'archive_sha256':ARCHIVE_SHA256,'dnbr_member':dnbr_member,'dnbr_member_sha256':digest(source/'dnbr.img'),
            'uploaded_severity_verified':True,'upload_provenance':upload_provenance,'original_project_sha256':original_hashes,
            'soil_artifacts_verified':len(soils),'identity':{'uid':os.getuid(),'gid':os.getgid(),'groups':os.getgroups()},
            'availability':bundle['availability'],'area_km2':bundle['area_km2'],'predictors':bundle['predictors'],
            'scenarios':scenarios,'normalization':normalization,'basin_normalized_dnbr_range':basin_range,
            'tool':bundle['tool'],'limitations':['Assessment dates are explicit; prior July 1 evidence is historical',
                                              'No production publication or automatic controller freshness enforcement']}
    (output/'evidence.json').write_text(json.dumps(report,indent=2,allow_nan=False)+'\n')
    print(json.dumps({'availability':bundle['availability'],'area_km2':bundle['area_km2'],
                      'predictors':{k:p['value'] for k,p in bundle['predictors'].items()},'output':str(output)}))


if __name__=='__main__':
    main()
