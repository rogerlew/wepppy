#!/usr/bin/env python3
"""Independent post-execution checks using retained manifests and artifacts."""
import hashlib
import json
from pathlib import Path
import re
import sys

root=Path(sys.argv[1])
def sha(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        for block in iter(lambda:f.read(1024*1024),b''):
            h.update(block)
    return h.hexdigest()

summary=json.loads((root/'execution-summary.json').read_text())
assert summary['source_unchanged'] and summary['output_mode_parity']
evidence={}
base=json.loads((root/'rr10/outputs.json').read_text())
for lane in ('rr10','rr17','rr60'):
    case=root/lane
    inputs=json.loads((case/'inputs.json').read_text())
    mismatch=[n for n,h in inputs['sha256'].items() if sha(case/'runs'/n)!=h]
    assert not mismatch, (lane,mismatch)
    changed_tokens=0
    for record in inputs['rrinit']:
        control=(case/'runs'/Path(record['file']).with_suffix('.run')).read_text().splitlines()
        assert [line.strip() for line in control if line.strip().endswith('.man')]==[record['file']]
        old=(root/'snapshot'/record['file']).read_bytes().splitlines(keepends=True)
        new=(case/'runs'/record['file']).read_bytes().splitlines(keepends=True)
        assert len(old)==len(new)
        for a,b in zip(old,new):
            if a==b:
                continue
            tokens=list(re.finditer(rb'\S+',a))
            assert len(tokens)==5 and float(tokens[3].group())==.1
            value={'rr17':b'0.17000','rr60':b'0.60000'}[lane]
            assert a[:tokens[3].start()]+value+a[tokens[3].end():]==b
            changed_tokens+=1
    assert changed_tokens==(0 if lane=='rr10' else 1885)
    terminals=[json.loads(p.read_text()) for p in (case/'logs').glob('*/terminal.json')]
    assert len(terminals)==865 and all(t['success'] for t in terminals)
    outputs=json.loads((case/'outputs.json').read_text())
    controls=[r['file'][1:-4] for r in inputs['rrinit'] if .1 not in r['before']]
    assert len(controls)==14
    names=[n for n in base if any(n.startswith(f'H{hill}.') for hill in controls)]
    assert names and all(outputs[n]==base[n] for n in names), lane
    warnings=[]
    errors=[]
    for p in sorted((case/'logs').glob('*/stderr')):
        if p.stat().st_size:
            errors.append({'run':p.parent.name,'text':p.read_text(errors='replace')[:1500]})
    for p in sorted((case/'logs').glob('*/stdout')):
        for line in p.read_text(errors='replace').splitlines():
            if re.search(r'\bwarning\b|\bnan\b|floating.point|SIGFPE',line,re.I):
                warnings.append({'run':p.parent.name,'line':line})
    evidence[lane]={'terminal_count':len(terminals),'input_hash_mismatches':mismatch,
                    'rrinit_tokens_changed_byte_verified':changed_tokens,
                    'negative_control_hillslopes':controls,'negative_control_output_files':len(names),
                    'stderr':errors,'warning_lines':warnings}
    assert not errors, lane
binaries=json.loads((root/'binaries.json').read_text())
assert all(sha(Path(binaries['root'])/n)==h for n,h in binaries['sha256'].items())
(root/'validation.json').write_text(json.dumps(evidence,indent=2)+'\n')
print(json.dumps(evidence,indent=2))
