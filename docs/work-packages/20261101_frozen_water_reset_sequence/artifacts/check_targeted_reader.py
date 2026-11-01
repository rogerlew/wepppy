"""Malformed hourly evidence must fail without a model invocation."""
import argparse,json
from pathlib import Path
from run_targeted_histories import read_window

def main(out):
    out.mkdir(parents=True,exist_ok=False);lines=[]
    for day in (19,20):
        for ofe in (1,2,3):
            for hour in range(1,25):
                for tag in ['BP_WBH_BEFORE_W','BP_WBH_PURK_W','BP_WBH_AFTER_W']:
                    for layer in range(1,11):lines.append(f'{tag} 3 {day} {ofe} {hour*100+layer} .1 .2 .3 .4 .5 .6')
                for tag in ['BP_WBH_ALLOC','BP_WBH_FLUX','BP_WBH_SEEP','BP_WBH_RETURN']:
                    lines.append(f'{tag} 3 {day} {ofe} {hour} 0 0 0 0 0 0')
    text='\n'.join(lines)+'\n';p=out/'valid.txt';p.write_text(text);result=read_window(p,3,20);assert len(result['hourly_records'])==144
    variants={'duplicate_layer':text+lines[0]+'\n','missing_layer':'\n'.join(lines[1:])+'\n',
        'missing_flux':text.replace(next(l+'\n' for l in lines if l.startswith('BP_WBH_FLUX')),''),
        'nonfinite':text.replace('.1 .2','NaN .2',1),'wrong_clock':text.replace('3 19 1','3 18 1',1)}
    receipts=[]
    for name,value in variants.items():
        p=out/(name+'.txt');p.write_text(value)
        try:read_window(p,3,20)
        except ValueError as e:receipts.append(dict(case=name,rejected=True,reason=str(e)))
        else:raise AssertionError(name)
    (out/'receipt.json').write_text(json.dumps(dict(passed=True,valid_hours=144,malformed=receipts),indent=2)+'\n');print('targeted reader controls passed')
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);main(p.parse_args().out)
