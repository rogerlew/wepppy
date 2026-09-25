"""Read-only independent M3 audit; writes only adjacent evidence files."""
import hashlib
import json
import math
from pathlib import Path
import numpy as np
import pandas as pd
import rasterio
from rasterio.warp import reproject, Resampling
from wepppy.nodb.mods.postfire_debris_flow import report

OUT = Path(__file__).resolve().parent
RUN = Path('/wc1/runs/th/thespian-cleanness')
MOD = RUN/'postfire_debris_flow'
ID = '8190121c8a4b45e1952861e74d909693'
P = MOD/'attempts'/ID/'predictors'
COEF = {15:(-3.71,.32,.33,.47),30:(-3.79,.21,.19,.36),60:(-3.46,.14,.10,.18)}
def sha(p):
    with p.open('rb') as f: return hashlib.file_digest(f,'sha256').hexdigest()
def clean(d):
    if isinstance(d,dict): return {k:clean(v) for k,v in d.items()}
    if isinstance(d,list): return [clean(v) for v in d]
    if isinstance(d,float) and not math.isfinite(d): return None
    return d
def save(n,d): (OUT/n).write_text(json.dumps(clean(d),indent=2,allow_nan=False)+'\n')
def read(p):
    with rasterio.open(p) as ds:
        return ds.read(1,masked=True), ds.profile

def main():
    tracked = sorted(p for p in RUN.rglob('*') if p.is_file() and (p.suffix in ('.cli','.par','.prn','.nodb','.tif','.parquet','.sqlite','.csv','.json','.geojson') or p.name.endswith(('-wal','-shm'))))
    before={str(p.relative_to(RUN)):sha(p) for p in tracked}
    if not (OUT/'protected_before.json').exists(): save('protected_before.json',before)
    before=json.loads((OUT/'protected_before.json').read_text())
    m=json.loads((MOD/'manifest.json').read_text()); pm=m['predictor_snapshot']
    assert json.loads((MOD/'attempts'/ID/'results/manifest.json').read_text()) == m
    save('result_manifest.json',m)
    hashes=[]
    for root in [MOD, P, P/'soil', P/'terrain']:
        manifest=json.loads((root/'manifest.json').read_text())
        for field in ['artifacts_sha256','sources_sha256']:
            for name,want in manifest.get(field,{}).items():
                path=Path(name) if name.startswith('/') else root/name
                hashes.append({'path':str(path),'matches':sha(path)==want})
    domain,g=read(P/'prepared/domain.tif'); basin=domain.filled(0)==1
    sbs,_=read(P/'prepared/sbs.tif'); thick,_=read(P/'soil/thickness_cm.tif')
    src,_=read(P/'soil/source.tif'); common,_=read(P/'valid_mask.tif')
    use=common.filled(0)==1
    expected=basin & ~np.ma.getmaskarray(sbs) & np.isfinite(thick.filled(np.nan)) & np.isin(src.filled(0),[1,2])
    assert np.array_equal(use,expected)
    watershed,_=read(P/'terrain/wbt/watershed.tif'); terrain_basin=watershed.filled(0)==1
    dem,_=read(P/'terrain/prepared/dem.tif')
    assert np.array_equal(terrain_basin,basin)
    area=int(basin.sum())*abs(g['transform'].a*g['transform'].e)
    relief=float(dem[terrain_basin].max()-dem[terrain_basin].min())
    T=relief/math.sqrt(area); F=float(np.count_nonzero(use & (sbs.filled(0)>=2))/use.sum()); S=float(thick[use].astype('float64').mean()/254)
    values={'T':T,'F':F,'S':S}
    for k,v in values.items(): assert math.isclose(v,pm['predictors'][k]['value'],abs_tol=1e-12)
    def probability(d,r,F=F,S=S):
        b,ct,cf,cs=COEF[d]; z=b+r*(ct*T+cf*F+cs*S)
        return 1/(1+math.exp(-z))
    tables={n:pd.read_parquet(MOD/(n+'.parquet')) for n in ['events','design','inverse']}
    checks={}
    for name,df in tables.items():
        errors=[]; units=[]
        for r in df.to_dict('records'):
            assert r['status']=='available'
            d=r['duration_minutes']; target=r['target_probability'] if name=='inverse' else r['probability']
            errors.append(abs(probability(d,r['rainfall_mm'])-target)); units.append(abs(r['rainfall_mm']-r['intensity_mm_per_hour']*d/60))
        checks[name]={'rows':len(df),'max_probability_error':max(errors),'max_unit_error_mm':max(units),'hash_match':sha(MOD/(name+'.parquet'))==m['tables'][name]['sha256'],'published_equals_attempt':sha(MOD/(name+'.parquet'))==sha(MOD/'attempts'/ID/'results'/(name+'.parquet'))}
        assert max(errors)<1e-12 and max(units)<1e-12
    cli=pd.read_parquet(RUN/'climate/wepp_cli.parquet'); event_errors=[]
    for r in tables['events'].to_dict('records'):
        c=cli.iloc[r['row_ordinal']]
        assert (r['year'],r['month'],r['day_of_month'],r['precipitation_mm'])==(c['year'],c['month'],c['day_of_month'],c['prcp'])
        event_errors.append(abs(r['intensity_mm_per_hour']-c[f"peak_intensity_{r['duration_minutes']}"]))
    design_errors=[]
    for r in tables['design'].to_dict('records'):
        ranked=sorted(cli.loc[cli.prcp>0,f"peak_intensity_{r['duration_minutes']}"],reverse=True)
        rank=m['frequency']['rank_indices'][str(float(r['return_interval_years']))]
        design_errors.append(abs(r['intensity_mm_per_hour']-ranked[rank]))
    coverage={'basin_cells':int(basin.sum()),'valid_cells':int(use.sum()),'excluded_cells':int((basin & ~use).sum()),'missing_sbs_cells':int((basin & np.ma.getmaskarray(sbs)).sum()),'missing_soil_cells':int((basin & ~np.isfinite(thick.filled(np.nan))).sum()),'sbs_counts':{str(v):int((basin & (sbs.filled(255)==v)).sum()) for v in [0,1,2,3,255]},'soil_sources_full':{str(v):int((basin & (src.filled(0)==v)).sum()) for v in [0,1,2]},'mean_thickness_common_cm':S*254,'mean_thickness_full_cm':float(thick[basin].astype('float64').mean())}
    a=report.open_assessment(RUN,'config',ID); views={}
    for d in COEF:
        q=dict(report.DEFAULT_QUERY,duration_minutes=d)
        payload=report.view(a,q); save(f'report_{d}.json',payload); views[str(d)]={'current':payload['summary']['current'],'status':payload['status']}
    save('numeric_audit.json',{'attempt_id':ID,'hash_checks':hashes,'predictors':values,'area_km2':area/1e6,'relief_m':relief,'coverage':coverage,'tables':checks,'max_event_rainfall_error':max(event_errors),'max_design_rainfall_error':max(design_errors),'inverse':tables['inverse'].to_dict('records'),'design':tables['design'].to_dict('records'),'views':views,'reference_intensity_scenarios':{str(i):probability(15,i/4) for i in [24,25.9,30,33.7,40]},'hypothetical_excluded_sbs_unburned':{'description':'Sensitivity only; missing SBS is NOT established unburned','F':F*int(use.sum())/int(basin.sum()),'S':float(thick[basin].astype('float64').mean()/254),'I15_P50':-COEF[15][0]/(COEF[15][1]*T+COEF[15][2]*F*int(use.sum())/int(basin.sum())+COEF[15][3]*float(thick[basin].astype('float64').mean()/254))*4}})
    after={str(p.relative_to(RUN)):sha(p) for p in tracked}
    save('preservation.json',{'files':len(tracked),'changed':[n for n in before if before[n]!=after[n]],'all_recorded_hashes_match':all(r['matches'] for r in hashes)})
    assert all(r['matches'] for r in hashes) and before == after
    assert max(event_errors)<1e-12 and max(design_errors)<1e-12
    assert all(v['current'] for v in views.values())
    print(json.dumps({'values':values,'coverage':coverage,'checks':checks,'preservation':before==after},indent=2))
if __name__=='__main__': main()
