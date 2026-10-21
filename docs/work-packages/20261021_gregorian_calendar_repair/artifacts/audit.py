"""Audit generated daily water/PASS dates against climate, without relying on exit status."""
from datetime import date, timedelta
from pathlib import Path
import argparse,json,re

def audit(root):
    rows={}
    for line in (root/'runs/p1.cli').read_text().splitlines()[15:]:
        f=line.split()
        if len(f)!=13:continue
        d,m,y=map(int,f[:3]);dt=date(y,m,d);key=(y,dt.timetuple().tm_yday)
        assert key not in rows,('duplicate climate',key)
        rows[key]=float(f[3])
    keys=list(rows)
    assert keys==[(d.year,d.timetuple().tm_yday) for d in
                 (date(keys[0][0],1,1)+timedelta(days=i) for i in range(len(keys)))]
    result={'climate_days':len(keys),'first':keys[0],'last':keys[-1],'water_files':{},'pass_files':{}}
    for p in sorted((root/'output').glob('H*.wat.dat')):
        ofes={}
        with p.open() as stream:
            for line in stream:
                f=line.split()
                if not f or not f[0].isdigit() or len(f)<20:continue
                ofe,day,year=map(int,f[:3]);key=(year,day)
                assert key in rows,(p,key)
                assert abs(float(f[3])-rows[key])<0.011,(p,key,f[3],rows[key])
                ofes.setdefault(ofe,[]).append(key)
        assert ofes,p
        for sequence in ofes.values():assert sequence==keys,(p,'wrong daily sequence')
        result['water_files'][p.name]={'ofes':len(ofes),'days_per_ofe':len(keys)}
    for p in sorted((root/'output').glob('*.pass.dat'))+list((root/'output').glob('pass_pw0.txt')):
        sequence=[]
        with p.open() as stream:
            for line in stream:
                if line[:8] in ('EVENT   ','SUBEVENT','NO EVENT'):
                    sequence.append((int(line[10:15]),int(line[16:21])))
        assert sequence==keys,(p,len(sequence),len(keys))
        result['pass_files'][p.name]=len(sequence)
    p=root/'output/ebe_pw0.txt'
    if p.exists():
        count=0
        for line in p.read_text().splitlines():
            f=line.split()
            if len(f)<10 or not f[0].isdigit():continue
            d,m,y=map(int,f[:3]);key=(y,date(y,m,d).timetuple().tm_yday)
            assert key in rows,(p,key)
            assert abs(float(f[3])-rows[key])<0.011,(p,key,f[3],rows[key])
            count+=1
        result['watershed_events']=count
    assert result['water_files']
    return result

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('root',type=Path);a=p.parse_args()
    result=audit(a.root);(a.root/'calendar-audit.json').write_text(json.dumps(result,indent=2));print(json.dumps(result))
