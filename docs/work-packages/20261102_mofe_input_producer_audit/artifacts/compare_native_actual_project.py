"""Run retained r5 against identical prepared copied-project inputs; compare raw water."""
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import argparse,hashlib,json,re,shutil
from wepp_runner.wepp_runner import run_hillslope

BASE=Path('/wc1/holdouts/mipa-native-r6-20261102')


def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()


def water(path):
    result={};header=None
    for line in path.open():
        values=line.split()
        if values[:3]==['OFE','J','Y']:header=values
        if not values or not values[0].isdigit():continue
        row=dict(zip(header,map(float,values)))
        key=int(row['OFE'])
        if key not in result:result[key]={'totals':dict.fromkeys(['Q','Ep','Es','Er','Dp','latqcc'],0.),'count':0}
        item=result[key];item['count']+=1
        for field in item['totals']:item['totals'][field]+=row[field]
        item['terminal_storage']=row['Total-Soil']
    return result


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--candidate-evidence',default='actual-project-v1')
    parser.add_argument('--result',default='actual-project-r5-v1')
    parser.add_argument('--expect-identical',action='store_true')
    args=parser.parse_args()
    source=Path('/wc1/runs/mi/mipa-awake-20261102/wepp')
    root=BASE/args.result;root.mkdir(exist_ok=False)
    runs=root/'runs';runs.mkdir();(root/'output').mkdir()
    manifest=json.loads((BASE/args.candidate_evidence/'inputs.json').read_text())
    for name,digest in manifest.items():
        path=source/'runs'/name;assert sha(path)==digest,(name,'source input drift')
        shutil.copyfile(path,runs/name)
    ids=sorted(int(p.stem[1:]) for p in runs.glob('p*.run'))
    assert len(ids)==72
    binary=BASE/'baseline-r5/vendored-wepp_261029_hill'
    def execute(i):
        result=run_hillslope(i,str(runs),wepp_bin=str(binary),timeout=300,timeout_retries=0)
        assert result[0],result
        return result
    with ThreadPoolExecutor(max_workers=4) as pool: results=list(pool.map(execute,ids))
    difference={}
    for i in ids:
        before=water(root/f'output/H{i}.wat.dat');after=water(source/f'output/H{i}.wat.dat')
        assert before.keys()==after.keys()
        for ofe,row in before.items():
            new=after[ofe];assert row['count']==new['count']
            difference[f'{i}:{ofe}']={'rows':row['count'],
                'delta_totals_mm':{field:new['totals'][field]-value for field,value in row['totals'].items()},
                'delta_terminal_storage_mm':new['terminal_storage']-row['terminal_storage']}
    outputs={p.name:sha(p) for p in (root/'output').iterdir()}
    current={p.name:sha(p) for p in (source/'output').iterdir() if p.is_file()}
    assert outputs.keys()==current.keys()
    receipt={'baseline_binary':str(binary),'baseline_binary_sha256':sha(binary),
        'candidate_binary_sha256':sha(BASE/'final-pair/wepp_261029_hill'),
        'identical_inputs':manifest,'hills':len(ids),'ofes':len(difference),
        'outputs':outputs,'candidate_outputs':current,
        'changed_outputs':[name for name in outputs if outputs[name]!=current[name]],
        'per_hill_ofe_water_differences':difference,'runner_results':results,
        'scope':'Same prepared inputs, retainedr5 versus finalr6; raw per-element diagnostics, not watershed outlet or full-budget closure.'}
    (root/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
    if args.expect_identical:
        assert not receipt['changed_outputs'],receipt['changed_outputs']
        assert all(not any(v['delta_totals_mm'].values()) and not v['delta_terminal_storage_mm']
                   for v in difference.values())
    print('Actual copied-project comparison completed',len(difference),'OFEs',len(receipt['changed_outputs']),'changed outputs')


if __name__=='__main__':main()
