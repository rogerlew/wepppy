"""Independent source oracle for actual HTTP/browser results, after live validation."""
import json
from pathlib import Path
import duckdb
import numpy as np
import pandas as pd

root=Path('/wc1/runs/mo/mofe-et-dp-validation-20261020')
out=root/'mofe-validation'
receipt=json.loads((out/'live-browser-receipt.json').read_text())
with duckdb.connect() as db:
    db.read_parquet(str(root/'wepp/output/interchange/H.wat.parquet')).create_view('wat')
    db.read_parquet(str(root/'watershed/hillslopes.parquet')).create_view('hill')
    daily=db.execute('''SELECT topaz_id,year,julian,water_year,sim_day_index,
        sum((Ep+Es+Er)*wat.Area)/sum(wat.Area) et,sum(Dp*wat.Area)/sum(wat.Area) dp
        FROM wat JOIN hill USING(wepp_id) GROUP BY ALL''').df()
divisor=max(daily.water_year.nunique()-1,1)
annual=daily.groupby('topaz_id')[['et','dp']].sum()/divisor
csv=pd.read_csv(out/'live-report.csv').set_index('TopazID').sort_index()
np.testing.assert_array_equal(csv.index,annual.index)
np.testing.assert_allclose(csv['Transpiration + Evaporation (mm)'],annual.et,rtol=1e-12)
np.testing.assert_allclose(csv['Percolation (mm)'],annual.dp,rtol=1e-12)
# HTML sort keys retain the underlying mm values independently of displayed units.
html=pd.DataFrame(receipt['reportRows'],columns=['TopazID',*csv.columns]).set_index('TopazID').sort_index()
np.testing.assert_allclose(html['Transpiration + Evaporation (mm)'],annual.et,rtol=1e-12)
np.testing.assert_allclose(html['Percolation (mm)'],annual.dp,rtol=1e-12)
event=daily[(daily.year==2002)&(daily.julian==182)].set_index('topaz_id')
state=receipt['state']
for field in [state['weppEventSummary'],state['baseSummaryCache']['weppEvent']]:
    assert len(field)==len(event)
    for topaz,row in field.items():
        np.testing.assert_allclose(row['event_ET'],event.loc[int(topaz),'et'],rtol=1e-12)
result={'html_csv_annual_hills':len(annual),'annual_divisor':int(divisor),
        'selected_and_baseline_event_hills':len(event),'independent_live_oracle':'pass',
        'download_hashes_verified':len(receipt['downloads'])}
(out/'live-oracle-receipt.json').write_text(json.dumps(result,indent=2))
print(json.dumps(result))
