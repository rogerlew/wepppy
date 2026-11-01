"""Read-only correction for decorative report stars in the retained SIFT histories."""
import argparse
import hashlib
import json
from pathlib import Path
import runpy


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--runs',required=True,type=Path);parser.add_argument('--out',required=True,type=Path)
    args=parser.parse_args();args.out.mkdir(parents=True,exist_ok=False)
    before={str(p.relative_to(args.runs)):(sha(p),p.stat().st_size,p.stat().st_mtime_ns)
            for p in args.runs.rglob('*') if p.is_file()}
    here=Path(__file__).resolve().parent
    original=here/'read_sift_native.py'
    namespace=runpy.run_path(str(original))
    # Preserve all original acceptance arithmetic. Replace only its output-token check
    # with a path-aware reader that recognizes the two documented report decorations.
    source=original.read_text()
    old="""            if '*' in token and set(token)=={'*'}:raise ValueError('Numeric output overflow')"""
    new="""            if '*' in token and set(token)=={'*'}:
                if path.name!='H1.loss.dat' or token not in {'**','***'}:
                    raise ValueError('Numeric output overflow')"""
    if source.count(old)!=1:raise ValueError('Original verifier changed')
    if sha(original)!='bf0e15c6a1c04b01d91bfd677e89a8464fefd55cd509bd84464af52a2280de83':raise ValueError('Original runner drift')
    # Source is this package's authored analysis code, never native model source.
    exec(compile(source.replace(old,new),str(original)+'[report-token-correction]','exec'),namespace)
    retained=json.loads((args.runs/'receipt.json').read_text());results=[]
    if [r['fixture']['name'] for r in retained['cases']]!=['zero','normal','high']:raise ValueError('Incomplete retained cases')
    for case in retained['cases']:
        root=args.runs/case['fixture']['name']
        if case['returncode']!=0 or not case['completion']:raise ValueError('Retained process failure')
        # Narrowly validate each excluded decoration in its actual report-line context.
        for path in (root/'output').iterdir():
            for line in path.read_text().splitlines():
                stars=[t for t in line.split() if set(t)=={'*'}]
                if not stars:continue
                text=line.strip()
                caution=text=='*** CAUTION ***'
                summary=text.startswith(('** Soil Loss (','** Maximum Soil Loss ','** Soil Deposition (','** Maximum Soil Deposition ')) and text.endswith(' **') and stars==['**','**']
                if path.name!='H1.loss.dat' or not (caution or summary):raise ValueError('Numeric or unknown star field: '+line)
        results.append(dict(name=case['fixture']['name'],passed=True,
            **namespace['validate'](root,case['fixture']['native_capped_mass_percent'])))
    after={str(p.relative_to(args.runs)):(sha(p),p.stat().st_size,p.stat().st_mtime_ns)
           for p in args.runs.rglob('*') if p.is_file()}
    if before!=after:raise ValueError('Retained artifact mutation')
    receipt=dict(cases=results,retained_inputs_outputs_unchanged=True,verified_members=len(before),
        original_receipt_sha256=sha(args.runs/'receipt.json'),reader_sha256=sha(Path(__file__)),
        original_runner_sha256=sha(original),correction='Known decorative report stars only; all original numeric acceptance retained')
    (args.out/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
    print(json.dumps({'cases':len(results),'passed':sum(r['passed'] for r in results)}))


if __name__=='__main__':main()
