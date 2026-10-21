"""Audit H1 water-balance date/precipitation against original climate rows."""
import datetime
import json
from pathlib import Path
import sys
r = Path(sys.argv[1])
clim = []
for line in (r/'runs/pw0.cli').read_text().splitlines()[15:]:
    if not line.strip():
        continue
    t = line.split()
    d,m,y = map(int,t[:3])
    clim.append({'date':[y,m,d], 'julian':datetime.date(y,m,d).timetuple().tm_yday,
                 'precip':float(t[3])})
wat = []
for line in (r/'output/H1.wat.dat').read_text().splitlines():
    t = line.split()
    if len(t)>5 and t[0]=='1' and t[1].isdigit() and t[2].isdigit():
        wat.append({'year':int(t[2]), 'julian':int(t[1]), 'precip':float(t[3])})
dates=[]; precip=[]
for i,(w,c) in enumerate(zip(wat,clim)):
    if [w['year'],w['julian']] != [c['date'][0],c['julian']]:
        dates.append({'ordinal':i+1,'water_balance':w,'climate':c})
    if abs(w['precip']-c['precip'])>0.011:
        precip.append({'ordinal':i+1,'water_balance':w,'climate':c})
print(json.dumps({'climate_rows':len(clim),'water_balance_rows':len(wat),
 'date_mismatch_count':len(dates),'first_date_mismatches':dates[:3],
 'precip_mismatch_count_within_input':len(precip),'first_precip_mismatches':precip[:3],
 'beyond_climate':wat[len(clim):], 'previous_block_tail':clim[-10:-8]},indent=2))
