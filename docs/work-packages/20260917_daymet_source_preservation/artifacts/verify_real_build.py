"""Build with real CLIGEN and retained 2021 observations, outside the live run."""
import hashlib,io,json,sys
from pathlib import Path
from unittest.mock import patch
import pandas as pd
from wepppy.climates.cligen import Cligen, CligenStationsManager
from wepppy.nodb.core.climate_build_helpers import build_observed_daymet
O=Path(__file__).resolve().parent
phase=sys.argv[1];assert phase in ('before','after')
D=O/phase;D.mkdir(exist_ok=True)
# Retained replay fixture: publisher 2021 precipitation, temperatures and
# radiation; unchanged dewpoint and wind from the audited Daymet build.
source=pd.read_parquet(O/'input_2021.parquet')
station=CligenStationsManager(version='2015_stations.db').get_station_fromid('co053359')
cligen=Cligen(station,wd=str(D))
with patch('wepppy.climates.daymet.retrieve_historical_timeseries',return_value=source.copy()):
 build_observed_daymet(cligen,-107.21618322112406,39.6392704740886,2021,2021,str(D),'ws.prn','wepp.cli',gridmet_wind=True,silent_pass_observed_quality_guard=True)
exported=pd.read_parquet(D/'daymet_2021-2021.parquet')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
result={'phase':phase,'source_equals_input':exported.equals(source),'cli_sha256':sha(D/'wepp.cli'),'prn_sha256':sha(D/'ws.prn'),'source_sha256':sha(D/'daymet_2021-2021.parquet'),'radiation_csv_exists':(D/'daymet_radiation_toa_normalization_wepp.csv').exists(),'cligen_quality_error':'*** ERROR ***' in (D/'cligen_wepp.log').read_text()}
if phase=='after':
 before=json.loads((O/'real_before.json').read_text())
 result['cli_bytes_unchanged']=result['cli_sha256']==before['cli_sha256']
 result['prn_bytes_unchanged']=result['prn_sha256']==before['prn_sha256']
 assert result['source_equals_input'] and result['cli_bytes_unchanged'] and result['prn_bytes_unchanged']
(O/f'real_{phase}.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
