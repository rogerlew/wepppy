import json, sys
from pathlib import Path
import pandas as pd
import duckdb
sys.path.insert(0, '/workdir/wepppyo3/release/linux/py312')
from wepppyo3.raster_characteristics import identify_mode_single_raster_key

wd = '/wc1/runs/un/unmodulated-price'
subwta = Path(f'{wd}/dem/topaz/SUBWTA.ARC')
nlcd = Path(f'{wd}/landuse/nlcd.tif')


def ensure_tif(path: Path) -> Path:
    """
    Convert ESRI ASCII grid (.ARC) to GeoTIFF for wepppyo3 if needed.
    Returns a Path to a GeoTIFF.
    """
    if path.suffix.lower() != '.arc':
        return path
    tif_path = path.with_suffix('.tif')
    if tif_path.exists():
        return tif_path
    import subprocess
    subprocess.run(['gdal_translate', '-of', 'GTiff', str(path), str(tif_path)], check=True)
    return tif_path


subwta = ensure_tif(subwta)
subwta = str(subwta)
nlcd = str(nlcd)

mode_map = identify_mode_single_raster_key(
    key_fn=subwta,
    parameter_fn=nlcd,
    ignore_channels=True,
    ignore_keys=set(),
    band_indx=1,
)
mode_map = {k: str(v) for k, v in mode_map.items()}

lu = json.loads(Path(f'{wd}/landuse.nodb').read_text())
state = lu.get('py/state', lu)
domlc_raw = state.get('domlc_d')
domlc = {str(k): str(v) for k, v in (domlc_raw or {}).items()}

con = duckdb.connect()
df = con.execute(
    """
    select cast(topaz_id as int) as topaz_id, cast(key as int) as key
    from parquet_scan(?)
    where topaz_id is not null and key is not null
    """,
    [f'{wd}/landuse/landuse.parquet'],
).fetchdf()
df['topaz_id'] = df['topaz_id'].astype(int).astype(str)
df['key'] = df['key'].astype(int).astype(str)
parquet_dom = dict(zip(df['topaz_id'], df['key']))

mismatch_dp = [(k, domlc.get(k), parquet_dom.get(k)) for k in set(domlc) | set(parquet_dom) if domlc.get(k) != parquet_dom.get(k)]
mismatch_pm = [(k, parquet_dom[k], mode_map.get(k)) for k in parquet_dom if mode_map.get(k) is not None and parquet_dom[k] != mode_map[k]]

print('domlc size', len(domlc), 'parquet size', len(parquet_dom), 'mode size', len(mode_map))
print('domlc vs parquet mismatches', len(mismatch_dp))
if mismatch_dp:
    print(' sample', mismatch_dp[:10])
print('parquet vs mode mismatches', len(mismatch_pm))
if mismatch_pm:
    print(' sample', mismatch_pm[:20])
