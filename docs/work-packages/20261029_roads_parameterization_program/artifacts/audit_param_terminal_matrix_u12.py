"""Independent exact-input terminal-support audit of completed U12 observations.

Partial mode reads only published case receipts. --complete additionally requires
all 1,188 results and rehashes every observer/reference input and output. This is
an error-bound inventory, not a physical/magnitude acceptance override.
"""
from decimal import Decimal, localcontext
from pathlib import Path
import argparse
import collections
import functools
import hashlib
import json
import math
import struct

P = Path('/workdir/wepppy/out/roads-parameterization-program-20261031')
ROOT = P/'param-sign-matrix-observe-u12'
CANDIDATE = P/'param-sign-u12-combined'
BUILD = P/'param-sign-observe-u12/build/src'
OUT = P/'param-terminal-matrix-audit-u12'
SOURCE_NAMES = ('param.for','depos.for','depeqs.for','depend.for','erod.for','runge.for','route.for')


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream,'sha256').hexdigest()


def f32(value):
    return struct.unpack('f',struct.pack('f',float(value)))[0]


def bits(value):
    return struct.unpack('I',struct.pack('f',value))[0]


def frombits(value):
    return struct.unpack('f',struct.pack('I',value))[0]


@functools.lru_cache(maxsize=32768)
def classify(line):
    tokens=line.split()
    assert tokens[0]=='NC_DEP' and len(tokens)==18, tokens
    year,day,ofe=map(int,tokens[1:4])
    xb,xe,begin,end,a,b,c,phi,theta,du,q,k,load,reported=map(float,tokens[4:])
    a,b,c,phi,theta,du,q,k,load=map(f32,(a,b,c,phi,theta,du,q,k,load))
    row=dict(year=year,day=day,ofe=ofe,xb=f32(xb),xe=f32(xe),wet_begin=begin,
             wet_end=end,a=a,b=b,c=c,phi=phi,theta=theta,du=du,q=q,ktrato=k,
             entry_load=load,observer_raw_minimum=reported,trace_line=line)
    reasons=[]
    if not all(math.isfinite(v) for v in (begin,end,a,b,c,phi,theta,du,q,k,load)):
        reasons.append('nonfinite state')
    if not (0<=begin<end<=1 and begin==f32(begin) and end==f32(end)):
        reasons.append('not a native normalized forward interval')
    if not (-1<=q<0 and phi<0 and end==-q and k>0):
        reasons.append('not a damped decreasing-flow interval ending exactly at dry boundary')
    if reasons:
        return dict(row,classification='requires_disposition',reasons=reasons)
    with localcontext() as context:
        context.prec=80
        A,B,C,K,BEGIN,END=map(Decimal.from_float,(a,b,c,k,begin,end))
        poly=lambda x:(A*x+B)*x+C
        derivative=lambda x:2*A*x+B
        minimum=poly(END)*K
        if not (poly(BEGIN)>=0 and minimum<0):
            return dict(row,classification='requires_disposition',
                        reasons=['negative support does not begin nonnegative and end negative'])
        whole_interval_monotone=max(derivative(BEGIN),derivative(END))<0
        if A==0:
            root=-C/B
        else:
            disc=B*B-4*A*C
            if disc<0:
                return dict(row,classification='requires_disposition',reasons=['no capacity root'])
            roots=[(-B-disc.sqrt())/(2*A),(-B+disc.sqrt())/(2*A)]
            inside=[r for r in roots if BEGIN<=r<END]
            if len(inside)!=1:
                return dict(row,classification='requires_disposition',reasons=['nonunique terminal-band root'])
            root=inside[0]
        if not BEGIN<=root<END:
            return dict(row,classification='requires_disposition',reasons=['root outside retained interval'])
        if max(derivative(root),derivative(END))>=0:
            return dict(row,classification='requires_disposition',
                        reasons=['negative band itself is not strictly decreasing'])
        if not whole_interval_monotone and not (A<0 and derivative(BEGIN)>=0):
            return dict(row,classification='requires_disposition',
                        reasons=['unclassified upstream support before terminal band'])
        # The root is unique in [BEGIN, END), capacity starts nonnegative,
        # and its derivative is negative on [root, END]. A positive upstream
        # hump therefore leaves the same monotone negative-band error proof.
        last=frombits(bits(end)-1)
        first=f32(root)
        if Decimal.from_float(first)<=root or poly(Decimal.from_float(first))>=0:
            first=frombits(bits(first)+1)
        count=max(0,bits(last)-bits(first)+1)
        coords=[frombits(v) for v in range(bits(first),bits(last)+1)] if count<=8 else [first,last]
        lastcap=poly(Decimal.from_float(last))*K
        bound=-minimum
        p=-Decimal.from_float(phi)
        d0=END-root
        s0=-K*derivative(END)
        s1=2*K*A
        errors=[]
        for coordinate in coords:
            delta=END-Decimal.from_float(coordinate)
            power=(p*(delta/d0).ln()).exp()
            def component(coefficient,degree):
                if p==degree:
                    return coefficient*delta**degree*(d0/delta).ln()
                return coefficient/(p-degree)*(delta**degree-d0**degree*power)
            error=component(s0,1)+component(s1,2)
            integral=-poly(Decimal.from_float(coordinate))*K
            assert Decimal(0)<=error<=integral<=bound
            errors.append(dict(coordinate=coordinate,integral_bound=str(integral),
                               raw_vs_clipped_model_error=str(error)))
        classification='seed_terminal_sliver' if count<=1 else 'wider_terminal_band_requires_disposition'
        reasons=[] if count<=1 else ['more than one negative native wet coordinate']
        if not whole_interval_monotone:
            classification='positive_hump_terminal_requires_disposition'
            reasons.append('positive upstream hump; negative band independently proved strictly decreasing')
        return dict(row,classification=classification,reasons=reasons,
                    support_shape='whole_interval_monotone' if whole_interval_monotone else 'positive_hump_then_terminal_band',
                    root=str(root),negative_width=str(END-root),terminal_raw_capacity=str(minimum),
                    last_wet_float32=last,last_wet_raw_capacity=str(lastcap),
                    negative_native_wet_points=count,negative_native_coordinates=coords,
                    integral_bound=str(bound),weighted_errors=errors)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--complete',action='store_true')
    args=parser.parse_args()
    declaration=json.loads((ROOT/'declaration.json').read_text())
    assert len(declaration['tasks'])==len(set(declaration['tasks']))==1188
    assert sha(BUILD/'wepp')==declaration['binary_sha256']
    OUT.mkdir(exist_ok=True)
    cases=[];records=[];pending=[]
    for source_text in declaration['tasks']:
        source=Path(source_text);relative=source.relative_to(CANDIDATE);folder=ROOT/relative
        receipt_path=folder/'receipt.json'
        if not receipt_path.exists():
            pending.append(str(relative));continue
        try:
            receipt=json.loads(receipt_path.read_text())
        except json.JSONDecodeError:
            if args.complete:raise
            pending.append(str(relative)+' (receipt publication incomplete)');continue
        assert receipt['source']==source_text and receipt['exact_output_parity'] is True
        assert receipt['binary_sha256']==declaration['binary_sha256']
        assert sha(source/'record.json')==receipt['source_record_sha256']
        reference=json.loads((source/'record.json').read_text())
        assert receipt['inputs']==reference['inputs'] and receipt['outputs']==reference['outputs']
        trace=folder/'trace.txt';assert sha(trace)==receipt['trace_sha256']
        lines=[line for line in trace.read_text().splitlines() if line.startswith('NC_DEP')]
        assert len(lines)==receipt['negative_capacity_calls']
        if args.complete:
            for case_folder in (folder,source):
                assert {p.name for p in (case_folder/'output').iterdir() if p.is_file()}==set(receipt['outputs'])
            for key,directory in [('inputs','runs'),('outputs','output')]:
                for name,digest in receipt[key].items():
                    assert Path(name).name==name
                    assert sha(folder/directory/name)==digest
                    assert sha(source/directory/name)==digest
        for index,line in enumerate(lines):
            records.append(dict(case=str(relative),negative_call_index=index,
                                trace_sha256=receipt['trace_sha256'],**classify(line)))
        cases.append(dict(case=str(relative),source=source_text,receipt_sha256=sha(receipt_path),
                          source_record_sha256=receipt['source_record_sha256'],
                          trace_sha256=receipt['trace_sha256'],negative_calls=len(lines)))
    final_path=ROOT/'results.json'
    source_manifest=json.loads((CANDIDATE/'source.json').read_text())
    candidate_sources={name:sha(CANDIDATE/'build/src'/name) for name in SOURCE_NAMES}
    assert all(candidate_sources[name]==source_manifest['files'][name] for name in SOURCE_NAMES)
    build_manifest=json.loads((CANDIDATE/'build.json').read_text())
    candidate_binaries={name:sha(CANDIDATE/'bin'/name) for name in build_manifest['binaries']}
    assert candidate_binaries==build_manifest['binaries']
    if args.complete:
        assert not pending and final_path.exists()
        final=json.loads(final_path.read_text());assert len(final)==1188
        mapping={r['source']:r for r in final};assert set(mapping)==set(declaration['tasks'])
        for case in cases:
            assert mapping[case['source']]==json.loads((ROOT/case['case']/'receipt.json').read_text())
    structured=[r for r in records if 'integral_bound' in r]
    flagged=[r for r in records if r['classification']!='seed_terminal_sliver']
    maximum=lambda values:max(values,default=0)
    summary=dict(expected_cases=1188,completed_cases=len(cases),pending_cases=len(pending),
                 final_inventory_verified=args.complete,all_input_output_bytes_rehashed=args.complete,
                 negative_calls=len(records),classification_counts=dict(collections.Counter(r['classification'] for r in records)),
                 negative_calls_by_panel=dict(collections.Counter(r['case'].split('/')[0] for r in records)),
                 negative_calls_by_soil=dict(collections.Counter(r['case'].split('/')[1].split('-')[1] for r in records)),
                 native_wet_coordinate_count_histogram=dict(collections.Counter(r['negative_native_wet_points'] for r in structured)),
                 support_shape_counts=dict(collections.Counter(r['support_shape'] for r in structured)),
                 calls_with_negative_native_wet_coordinate=sum(r['negative_native_wet_points']>0 for r in structured),
                 max_negative_native_wet_coordinates=maximum(r['negative_native_wet_points'] for r in structured),
                 max_negative_width=maximum(float(r['negative_width']) for r in structured),
                 max_continuous_terminal_integral_bound=maximum(float(r['integral_bound']) for r in structured),
                 max_native_wet_integral_bound=maximum(float(e['integral_bound']) for r in structured for e in r['weighted_errors']),
                 max_native_wet_weighted_model_error=maximum(float(e['raw_vs_clipped_model_error']) for r in structured for e in r['weighted_errors']),
                 disposition='Evidence inventory only; no physical/magnitude criterion is waived.')
    result=dict(summary=summary,script_sha256=sha(Path(__file__)),declaration_sha256=sha(ROOT/'declaration.json'),
                observer_binary_sha256=sha(BUILD/'wepp'),observer_sources={n:sha(BUILD/n) for n in SOURCE_NAMES},
                candidate_sources=candidate_sources,candidate_binaries=candidate_binaries,
                candidate_source_manifest_sha256=sha(CANDIDATE/'source.json'),
                candidate_build_manifest_sha256=sha(CANDIDATE/'build.json'),
                final_results_sha256=sha(final_path) if args.complete else None,
                cases=cases,negative_support=records,flagged=flagged,pending=pending)
    filename='final-receipt.json' if args.complete else 'progress-receipt.json'
    temp=OUT/(filename+'.tmp');temp.write_text(json.dumps(result,indent=2,allow_nan=False)+'\n');temp.replace(OUT/filename)
    print(json.dumps(summary,indent=2),flush=True)
    if flagged:
        print('FLAGGED',json.dumps([{k:r[k] for k in ('case','year','day','ofe','classification','reasons')} for r in flagged[:30]],indent=2),flush=True)


if __name__=='__main__':main()
