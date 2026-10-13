"""Experimental EDDE daily replay; see ADR-0091 for scientific limitations."""
from pathlib import Path

import numpy as np
import pandas as pd

from wepppy.climates.cligen import Cligen, ClimateFile, df_to_prn
from .client import DataQualityError, sha256, write_json


def read_cli(path: str | Path) -> pd.DataFrame:
    """Read daily values with a calendar index (ClimateFile uses RangeIndex)."""
    frame = ClimateFile(str(path)).as_dataframe()
    frame.index = pd.DatetimeIndex(pd.to_datetime(dict(year=frame.year, month=frame.mo, day=frame.da)))
    return frame


def _validate_cli(frame: pd.DataFrame) -> None:
    """Reject invalid replay artifacts before using or accepting a revision."""
    if frame.empty or not frame.index.equals(pd.date_range(frame.index[0], frame.index[-1])):
        raise DataQualityError('Climate dates must be nonempty, continuous and ordered')
    if not np.isfinite(frame.to_numpy(dtype=float)).all():
        raise DataQualityError('Climate contains nonfinite values')
    if (frame.prcp < 0).any() or (frame.tmin > frame.tmax).any():
        raise DataQualityError('Invalid climate precipitation/temperature values')
    wet = frame.prcp > 0
    if (frame.loc[wet, 'dur'] <= 0).any() or (frame.loc[wet, 'ip'] < 1).any():
        raise DataQualityError('Wet climate rows lack meaningful storm duration/intensity')


def normalize_daily(table: pd.DataFrame, manifests: list[dict]) -> pd.DataFrame:
    """Validate complete years and convert explicit native units for CLIGEN."""
    required = {'prday': ('PRECIP','kg m-2'), 'tsmax': ('T2MAX','K'), 'tsmin': ('T2MIN','K')}
    if not manifests or any(m.get('status') != 'complete' for m in manifests):
        raise DataQualityError('Complete query provenance is required')
    if len({(m['model'],m['scenario']) for m in manifests}) != 1:
        raise DataQualityError('Cannot mix driving model/scenario in one climate')
    for manifest in manifests:
        for name, expected in required.items():
            records = [obj for obj in manifest['objects'] if obj['variable']==name]
            if not records or any((r['netcdf_variable'],r['units']) != expected for r in records):
                raise DataQualityError(f'Unexpected {name} source variable or units')
    if table.empty or table['point'].nunique()!=1:
        raise DataQualityError('One nonempty point series is required')
    point = str(table['point'].iloc[0])
    if any(point not in {p['name'] for p in m['points']} for m in manifests):
        raise DataQualityError('Point is not covered by every query manifest')
    locations = [next(p for p in m['points'] if p['name']==point) for m in manifests]
    identity = ('longitude', 'latitude', 'row', 'col')
    if len({tuple(p[k] for k in identity) for p in locations}) != 1:
        raise DataQualityError('Cannot mix locations or native cells in one climate')
    covered = pd.DatetimeIndex(sorted({d for m in manifests
                                      for d in pd.date_range(m['start'], m['end'])}))
    if not covered.equals(pd.DatetimeIndex(pd.to_datetime(table['date']))):
        raise DataQualityError('Table dates differ from query manifest coverage')
    frame = table.copy()
    frame.index = pd.DatetimeIndex(pd.to_datetime(frame.pop('date')))
    if (frame.index[0].month,frame.index[0].day)!=(1,1) or (frame.index[-1].month,frame.index[-1].day)!=(12,31):
        raise DataQualityError('Replay requires complete calendar years')
    if not frame.index.equals(pd.date_range(frame.index[0],frame.index[-1])):
        raise DataQualityError('Replay requires continuous ordered dates')
    values=frame[list(required)].to_numpy(dtype=float)
    if not np.isfinite(values).all() or (frame.prday<0).any() or (frame.tsmin>frame.tsmax).any():
        raise DataQualityError('Invalid precipitation/temperature values')
    return pd.DataFrame({'prcp_mm':frame.prday,'tmax':frame.tsmax-273.15,
                         'tmin':frame.tsmin-273.15}, index=frame.index)


def build_climate(table: pd.DataFrame, manifests: list[dict], station, output: str | Path,
                  *, seed: int) -> dict:
    """Generate in a new directory; preserve failed diagnostics and source input."""
    root=Path(output)
    root.mkdir(parents=True,exist_ok=False)
    state=dict(status='incomplete', method='EDDE daily replay, experimental', seed=seed,
               point=str(table.point.iloc[0]) if len(table) else None,
               station=station.as_dict(), sources=manifests,
               generated_fields=['dur','tp','ip','rad','w-vl','w-dir','tdew'],
               limitations=['No bias correction','Future changes in station-derived auxiliary fields are unvalidated',
                            'CLI header location is the auxiliary station; source point/cell is in sources'])
    write_json(root/'manifest.json',state)
    table.to_csv(root/'source-daily.csv',index=False)
    frame=normalize_daily(table,manifests)
    frame.to_csv(root/'normalized-daily.csv',index_label='date')
    df_to_prn(frame.copy(),str(root/'daily.prn'),'prcp_mm','tmax','tmin',
              pad_to_end_of_year=False,reject_internal_missing=True)
    runner=Cligen(station,wd=str(root.resolve()),cliver='5.3.2')
    runner.run_observed('daily.prn',cli_fn='wepp.cli',randseed=seed,
                        adjust_mx_pt5=False,silently_pass_quality_guard=False,
                        timeout=120,timeout_retries=0)
    parsed=read_cli(root/'wepp.cli')
    if not parsed.index.equals(frame.index):
        raise DataQualityError('Generated CLI dates differ from source dates')
    differences={}
    for source,target,bound in [('prcp_mm','prcp',.1771),('tmax','tmax',.3279),('tmin','tmin',.3279)]:
        delta=float(np.max(abs(parsed[target].to_numpy()-frame[source].to_numpy())))
        differences[target]=delta
        if delta>bound:
            raise DataQualityError(f'CLIGEN {target} differs beyond format rounding: {delta}')
    if not np.isfinite(parsed.to_numpy(dtype=float)).all():
        raise DataQualityError('Generated climate contains nonfinite values')
    wet=parsed.prcp>0
    if (parsed.loc[wet,'dur']<=0).any() or (parsed.loc[wet,'ip']<1).any():
        raise DataQualityError('Wet climate rows lack meaningful storm duration/intensity')
    state.update(status='complete',days=len(parsed),maximum_source_error=differences,
                 source_wet_days=int((frame.prcp_mm>0).sum()),cli_wet_days=int(wet.sum()),
                 binary_sha256=sha256(Path(runner.cligen532)),
                 files={p.name:sha256(p) for p in root.iterdir() if p.is_file() and p.name!='manifest.json'})
    write_json(root/'manifest.json',state)
    return state


def revise_prism(source: str | Path, output: str | Path, reference: dict, target: dict) -> dict:
    """Apply existing Multiple PRISM arithmetic using explicit monthly normals.

    Each normals object contains ppt/tmax/tmin (12 monthly values) and provenance.
    Both temperature arrays are Celsius; precipitation arrays use the same units.
    """
    for normals in (reference,target):
        provenance = normals.get('provenance')
        if not isinstance(provenance, dict) or not all(
                provenance.get(key) for key in ('period', 'units', 'sha256')):
            raise DataQualityError('PRISM normals period, units, and source hash are required')
        if provenance['units'] != {'ppt':'mm/month', 'tmax':'C', 'tmin':'C'}:
            raise DataQualityError('Expected PRISM monthly mm and Celsius normals')
        for name in ('ppt','tmax','tmin'):
            values=np.asarray(normals[name],dtype=float)
            if values.shape!=(12,) or not np.isfinite(values).all():
                raise DataQualityError('Require twelve finite monthly PRISM normals')
        if np.any(np.asarray(normals['ppt'])<0) or np.any(np.asarray(normals['tmin'])>normals['tmax']):
            raise DataQualityError('Invalid PRISM precipitation/temperature normals')
    if reference['provenance']['period'] != target['provenance']['period']:
        raise DataQualityError('PRISM reference and target periods must match')
    if np.any(np.asarray(reference['ppt'])<=0):
        raise DataQualityError('Reference PRISM precipitation must be positive')
    path=Path(output)
    companion = path.with_suffix('.prism.json')
    if path.exists() or companion.exists() or Path(source).resolve() in (path.resolve(), companion.resolve()):
        raise ValueError('PRISM output must be a new file distinct from source')
    cli=ClimateFile(str(source))
    frame=read_cli(source)
    _validate_cli(frame)
    months=pd.DatetimeIndex(frame.index).month.to_numpy()-1
    dates=[(d.year,d.month,d.day) for d in frame.index]
    ratio=np.asarray(target['ppt'])/np.asarray(reference['ppt'])
    expected={
        'prcp':frame.prcp.to_numpy()*ratio[months],
        'tmax':frame.tmax.to_numpy()+(np.asarray(target['tmax'])-reference['tmax'])[months],
        'tmin':frame.tmin.to_numpy()+(np.asarray(target['tmin'])-reference['tmin'])[months],
    }
    if not all(np.isfinite(values).all() for values in expected.values()):
        raise DataQualityError('PRISM revision produced nonfinite values')
    inverted = np.flatnonzero(expected['tmin'] > expected['tmax'])
    if len(inverted):
        first = int(inverted[0])
        maximum = float(np.max(expected['tmin'] - expected['tmax']))
        raise DataQualityError(
            f'PRISM revision would invert temperature extrema on {len(inverted)} days; '
            f'first={frame.index[first].date()}, maximum inversion={maximum:.3f} C')
    for name,values in expected.items():cli.replace_var(name,dates,values)
    cli.write(str(path))
    actual=read_cli(path)
    _validate_cli(actual)
    if not actual.index.equals(frame.index):
        raise DataQualityError('PRISM output dates differ from source dates')
    errors={name:float(np.max(abs(actual[name]-values))) for name,values in expected.items()}
    if any(error>.05001 for error in errors.values()):
        raise DataQualityError('PRISM output does not match spatial revision within CLI rounding')
    result=dict(status='complete',source_sha256=sha256(Path(source)),output_sha256=sha256(path),
                reference=reference,target=target,maximum_rounding_error=errors)
    write_json(companion,result)
    return result
