#!/usr/bin/env python3
"""Offline frozen-input study. Uses owned Rust counting; never acquires data."""
import argparse
import csv
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import sqlite3
import subprocess

import numpy as np
import rasterio
from rasterio.warp import reproject, Resampling
from wepppyo3.raster_characteristics import count_intersecting_raster_key_pairs

REPO = Path(__file__).resolve().parents[4]
# Load the pure helper without importing NoDb's package-level Redis bootstrap.
spec = importlib.util.spec_from_file_location('offline_soils', REPO/'wepppy/nodb/mods/postfire_debris_flow/soil_thickness.py')
soil = importlib.util.module_from_spec(spec)
spec.loader.exec_module(soil)
COEFFICIENTS = [(15, -3.71, .32, .33, .47), (30, -3.79, .21, .19, .36), (60, -3.46, .14, .10, .18)]
SITES = ['moscow_mountain', 'topanga', 'az_ponderosa']


def rows(path):
    with Path(path).open() as stream:
        return list(csv.DictReader(stream))


def write_csv(path, records):
    with Path(path).open('w', newline='') as stream:
        writer=csv.DictWriter(stream,fieldnames=list(records[0]));writer.writeheader();writer.writerows(records)


def database(fixtures, site, target):
    """Reconstruct disposable SQLite from inspectable, frozen public tables."""
    if target.exists():
        raise FileExistsError(target)
    with sqlite3.connect(target) as db:
        for table in ['component', 'chorizon']:
            data=rows(fixtures/f'{site}_{table}.csv')
            columns=list(data[0])
            db.execute(f"CREATE TABLE {table} ({','.join(c+' TEXT' for c in columns)})")
            db.executemany(f"INSERT INTO {table} VALUES ({','.join('?' for _ in columns)})",
                           [[r[c] or None for c in columns] for r in data])
    return target


def write_raster(path, data, profile, nodata=None):
    with rasterio.open(path,'w',**dict(profile,dtype=data.dtype,count=1,nodata=nodata,compress='deflate')) as dst:
        dst.write(data,1)


def statsgo(fixtures,site,profile,shape):
    """Average value*support and support independently; no nodata bridging."""
    with rasterio.open(fixtures/f'{site}_statsgo_native.tif', driver='GTiff') as src:
        a=src.read(1);valid=np.isfinite(a)&(a>=0)
        numerator=np.zeros(shape,dtype='float64');support=np.zeros(shape,dtype='float64')
        for source,target in [(np.where(valid,a*2.54,0),numerator),(valid.astype('float64'),support)]:
            reproject(source,target,src_transform=src.transform,src_crs=src.crs,
                      dst_transform=profile['transform'],dst_crs=profile['crs'],
                      resampling=Resampling.average)
    mean=np.full(shape,np.nan)
    np.divide(numerator,support,out=mean,where=support>0)
    return mean,support


def aggregate(mask, values, weights, output, profile, name):
    """Rust category counts; each category identifies a value/support pair."""
    # NumPy encodes continuous pairs in compiled array operations. Rust traverses
    # mask intersections, and Python reduces only the resulting category table.
    pairs=np.stack([np.nan_to_num(values,nan=-1).ravel(),weights.ravel()],axis=1)
    unique,inverse=np.unique(pairs,axis=0,return_inverse=True)
    path=output/f'{name}_categories.tif'
    write_raster(path,(inverse.reshape(values.shape)+1).astype('int32'),profile)
    counts=count_intersecting_raster_key_pairs(str(mask),str(path),ignore_channels=False).get('1',{})
    support=numerator=0.
    for key,count in counts.items():
        value,weight=unique[int(key)-1]
        if weight>0 and value>=0:
            support+=count*weight;numerator+=count*weight*value
    path.unlink()
    return (numerator/support if support else None),support,sum(counts.values())


def probability(x):
    return 1/(1+math.exp(-x)) if x>=0 else math.exp(x)/(1+math.exp(x))


def scenarios(row, t):
    if row['ssurgo_mean_cm'] is None or row['statsgo_mean_cm'] is None:
        return []
    result=[]
    for duration,b,ct,cf,cs in COEFFICIENTS:
        d0=ct*t+cf*.5+cs*row['statsgo_mean_cm']/254
        d1=ct*t+cf*.5+cs*row['ssurgo_mean_cm']/254
        if not math.isfinite(d0+d1) or min(d0,d1)<=0:
            raise ValueError('Invalid M3 denominator')
        rainfall=[('fixed_5',5.),('fixed_10',10.),('fixed_20',20.)]
        for target in [.5,.75]:
            numerator=math.log(target/(1-target))-b
            r0=numerator/d0;r1=numerator/d1
            if min(r0,r1)<0:raise ValueError('Negative inverse threshold')
            rainfall.append((f'reference_p{target}',r0))
            result.append(dict(site=row['site'],outlet=row['outlet'],policy=row['policy'],
                support_mode=row['support_mode'],outside_area_range=row['outside_area_range'],
                duration_min=duration,scenario=f'inverse_p{target}',F=.5,T=t,
                reference_S=row['statsgo_mean_cm']/254,ssurgo_S=row['ssurgo_mean_cm']/254,
                rainfall_mm=None,reference_probability=target,ssurgo_probability=None,delta_probability_pp=None,
                reference_threshold_mm=r0,ssurgo_threshold_mm=r1,delta_threshold_mm=r1-r0,
                delta_threshold_mm_hour=(r1-r0)/(duration/60),delta_threshold_pct=100*(r1/r0-1)))
        for name,r in rainfall:
            p0,p1=probability(b+r*d0),probability(b+r*d1)
            result.append(dict(site=row['site'],outlet=row['outlet'],policy=row['policy'],
                support_mode=row['support_mode'],outside_area_range=row['outside_area_range'],
                duration_min=duration,scenario=name,F=.5,T=t,
                reference_S=row['statsgo_mean_cm']/254,ssurgo_S=row['ssurgo_mean_cm']/254,
                rainfall_mm=r,reference_probability=p0,ssurgo_probability=p1,delta_probability_pp=100*(p1-p0),
                reference_threshold_mm=None,ssurgo_threshold_mm=None,delta_threshold_mm=None,
                delta_threshold_mm_hour=None,delta_threshold_pct=None))
    return result


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--fixtures',type=Path,default=REPO/'tests/nodb/mods/fixtures/postfire_debris_flow_soils')
    parser.add_argument('--terrain',type=Path,default=Path('/workdir/weppcloud-wbt/test_fixtures/staley_m3_resolution'))
    parser.add_argument('--wbt',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    # Verify snapshots before creating any derived files.
    for f in json.loads((args.fixtures/'manifest.json').read_text())['files']:
        if soil._hash(args.fixtures/f['path']) != f['sha256']:raise ValueError('Fixture hash mismatch')
    terrain_hashes={}
    terrain_manifest=json.loads((args.terrain/'manifest.json').read_text())
    for run in terrain_manifest['runs']:
        if run['resolution_m'] != 10:continue
        for entry in run['files']:
            if entry['source_relative_path'] == 'dem/dem.tif':
                path=args.terrain/entry['path']
                actual=soil._hash(path)
                if actual != entry['sha256']:raise ValueError('Terrain fixture hash mismatch')
                terrain_hashes[str(path)]=actual
    args.output.mkdir(parents=True,exist_ok=False)
    reference=rows(REPO/'docs/work-packages/20260908_staley_m3_wbt_terrain/artifacts/resolution_comparison.csv')
    reference=[r for r in reference if r['comparison']=='controlled']
    comparisons=[];sensitivity=[];coverage=[];components=[];units=[];commands=[]
    for site in SITES:
        directory=args.output/site;directory.mkdir()
        cache=database(args.fixtures,site,directory/'source.sqlite')
        with rasterio.open(args.fixtures/f'{site}_mukey.tif', driver='GTiff') as ds:
            profile=ds.profile;shape=ds.shape
        conditioned=directory/'conditioned.tif';pointer=directory/'pointer.tif'
        for tool, params in [('FillDepressions', [f"--dem={args.terrain/site/'10m/dem/dem.tif'}",f'--output={conditioned}','--fix_flats=true','--flat_increment=0.00001']),
                             ('D8Pointer',[f'--dem={conditioned}',f'--output={pointer}'])]:
            command=[str(args.wbt.resolve()),f'-r={tool}','--compress_rasters=false',*params]
            completed=subprocess.run(command,capture_output=True,text=True,check=True)
            (directory/f'{tool}.log').write_text(completed.stdout+completed.stderr)
            commands.append(command)
        masks={}
        for r in reference:
            if r['site']!=site:continue
            pour=np.zeros(shape,dtype='int32');pour[int(r['row10']),int(r['col10'])]=1
            p=directory/f"{r['outlet']}_pour.tif";m=directory/f"{r['outlet']}_mask.tif"
            write_raster(p,pour,profile,0)
            command=[str(args.wbt.resolve()),'-r=Watershed',f'--d8_pntr={pointer}',f'--pour_pts={p}',f'--output={m}']
            completed=subprocess.run(command,capture_output=True,text=True,check=True)
            (directory/f"{r['outlet']}_wbt.log").write_text(completed.stdout+completed.stderr)
            commands.append(command);masks[r['outlet']]=m
            with rasterio.open(m, driver='GTiff') as ds:
                if np.count_nonzero(ds.read(1)==1)!=int(r['cells10']):raise ValueError('Terrain mask count mismatch')
        reference_cm,reference_support=statsgo(args.fixtures,site,profile,shape)
        write_raster(directory/'statsgo_cm.tif',reference_cm.astype('float32'),profile,float('nan'))
        write_raster(directory/'statsgo_support.tif',reference_support.astype('float32'),profile)
        for policy in ['strict_soil','all_layers']:
            target=directory/policy
            built=soil.build_artifacts(cache,args.fixtures/f'{site}_mukey.tif',masks,target,
                                       source_id=f'NRCS_2025_mosaic_SDA_snapshot_{site}',policy=policy)
            coverage.extend(dict(site=site,**r) for r in built)
            components.extend(dict(site=site,policy=policy,**r) for r in rows(target/'components.csv'))
            units.extend(dict(site=site,policy=policy,**r) for r in rows(target/'mapunits.csv'))
            with rasterio.open(target/'thickness_cm.tif') as ds:ssurgo=ds.read(1).astype('float64')
            with rasterio.open(target/'valid_fraction.tif') as ds:valid=ds.read(1).astype('float64')
            for r in reference:
                if r['site']!=site:continue
                mask=masks[r['outlet']]
                for mode in ['common_support','known_support','full_support']:
                    # Strict common support admits only fully covered reference cells;
                    # component locations within MUKEY remain unknown. Use identical
                    # fractional component weights for both means on that support.
                    w1=valid.copy();w0=reference_support.copy()
                    if mode=='common_support':
                        w1=np.where(reference_support>=1-1e-12,valid,0);w0=w1.copy()
                    mean1,n1,total=aggregate(mask,ssurgo,w1,directory,profile,'ssurgo')
                    mean0,n0,total0=aggregate(mask,reference_cm,w0,directory,profile,'statsgo')
                    if total != total0 or total != int(r['cells10']):raise ValueError('Lost aggregation denominator')
                    if mode=='full_support':
                        if not math.isclose(n1,total,abs_tol=1e-5,rel_tol=0):mean1=None
                        if not math.isclose(n0,total,abs_tol=1e-5,rel_tol=0):mean0=None
                    row=dict(site=site,outlet=r['outlet'],policy=policy,support_mode=mode,
                             outside_area_range=not .02<=float(r['area10_m2'])/1e6<=8,
                             area_m2=float(r['area10_m2']),ssurgo_mean_cm=mean1,statsgo_mean_cm=mean0,
                             delta_cm=mean1-mean0 if mean1 is not None and mean0 is not None else None,
                             ssurgo_S=mean1/254 if mean1 is not None else None,
                             statsgo_S=mean0/254 if mean0 is not None else None,
                             ssurgo_coverage=n1/total,statsgo_coverage=n0/total,
                             status='paired' if mean1 is not None and mean0 is not None else 'unavailable',
                             reason='complete_only_policy' if mode=='full_support' and mean1 is None else '')
                    comparisons.append(row);sensitivity.extend(scenarios(row,float(r['t10'])))
    write_csv(args.output/'source_comparison.csv',comparisons)
    write_csv(args.output/'m3_sensitivity.csv',sensitivity)
    write_csv(args.output/'catchment_coverage.csv',coverage)
    write_csv(args.output/'component_audit.csv',components)
    write_csv(args.output/'mapunit_audit.csv',units)
    (args.output/'commands.json').write_text(json.dumps(commands,indent=2)+'\n')
    (args.output/'environment.json').write_text(json.dumps(dict(wbt_sha256=soil._hash(args.wbt),
        fixture_manifest_sha256=soil._hash(args.fixtures/'manifest.json'),
        terrain_inputs=terrain_hashes,reference_outlets_sha256=soil._hash(REPO/'docs/work-packages/20260908_staley_m3_wbt_terrain/artifacts/resolution_comparison.csv'),
        script_sha256=soil._hash(__file__),helper_sha256=soil._hash(REPO/'wepppy/nodb/mods/postfire_debris_flow/soil_thickness.py')),
        indent=2)+'\n')
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig,axes=plt.subplots(1,2,figsize=(11,4))
    for policy in ['strict_soil','all_layers']:
        data=[r for r in comparisons if r['policy']==policy and r['support_mode']=='common_support' and r['status']=='paired']
        axes[0].scatter([r['statsgo_mean_cm'] for r in data],[r['ssurgo_mean_cm'] for r in data],label=policy)
        axes[1].scatter([r['area_m2']/1e6 for r in data],[r['ssurgo_coverage'] for r in data],label=policy)
    axes[0].plot([0,250],[0,250],color='gray');axes[0].set(xlabel='STATSGO cm',ylabel='SSURGO cm (common support)')
    axes[1].set(xscale='log',xlabel='Catchment km²',ylabel='Valid equivalent fraction')
    for ax in axes:ax.legend()
    fig.tight_layout();fig.savefig(args.output/'soil_comparison.png',dpi=160);plt.close(fig)
    for f in json.loads((args.fixtures/'manifest.json').read_text())['files']:
        if soil._hash(args.fixtures/f['path']) != f['sha256']:raise ValueError('Fixture changed')
    if any(soil._hash(path)!=digest for path,digest in terrain_hashes.items()):raise ValueError('Terrain inputs changed')
    print(f'{len(comparisons)} comparisons; {len(sensitivity)} diagnostic scenarios')


if __name__=='__main__':main()
