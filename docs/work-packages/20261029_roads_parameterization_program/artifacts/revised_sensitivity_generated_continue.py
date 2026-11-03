"""Retain failed G readback and supply its actual native calendar to readers."""
import argparse
from pathlib import Path
import shutil

import revised_sensitivity as s

DECLARATION=s.ROOT/'declaration-v4.json'
REVIEW=s.ROOT/'generated-continuation-review.json'


def declare():
    old=s.ROOT/'declaration-v3.json'
    d=s.seeds.read(old)
    s.verify_dependencies(d['dependencies'])
    assert len([r for r in d['tasks'] if (Path(r['root'])/'result.json').exists()])==40
    original=d['tasks'][40]
    assert (original['context'],original['arm'])==('G','exact')
    source=Path(original['root'])
    failed=s.seeds.read(source/'continuation-failure.json')
    assert failed['message']=='EBE date missing or duplicate'
    prior=s.seeds.read(source/'native-result.json')
    assert {Path(k).name:v for k,v in prior['output_sha256'].items()}==prior['original_outputs']
    s.h.verify(source,prior['output_sha256'])
    dependencies=dict(d['dependencies'])
    dependencies[str(Path(__file__).resolve())]=s.h.digest(__file__)
    bindings={}
    for row in d['tasks']:
        src=Path(row['root'])
        if row['context']!='G':
            result=s.seeds.read(src/'result.json')
            s.h.verify(src,result['response']['event_tables'])
            bindings[str(src/'result.json')]=s.h.digest(src/'result.json')
            continue
        dest=s.ROOT/'recovered/G'/row['arm']
        dest.mkdir(parents=True,exist_ok=False)
        for relative in ('wepp/roads/runs','wepp/roads/output','wepp/roads/segments','climate'):
            (dest/relative).mkdir(parents=True,exist_ok=True)
        for name,digest in row['record']['prepared_files'].items():
            target=dest/'wepp/roads/runs'/name
            shutil.copyfile(src/'wepp/roads/runs'/name,target)
            assert s.h.digest(target)==digest
        for name in ('prepared.json','final-prepared.json'):
            shutil.copyfile(src/name,dest/name)
        # Native reads runs/p1.cli. Owned interchange readers additionally discover
        # project/climate, so their context must contain that same exact calendar.
        shutil.copyfile(dest/'wepp/roads/runs/p1.cli',dest/'climate/site.cli')
        calendar=s.climate_for(row)
        assert s.h.digest(dest/'climate/site.cli')==calendar['sha256']
        bindings[str(dest/'climate/site.cli')]=calendar['sha256']
        if row['arm']=='exact':
            for relative,digest in prior['output_sha256'].items():
                shutil.copyfile(src/relative,dest/relative)
                assert s.h.digest(dest/relative)==digest
                bindings[str(src/relative)]=digest
            for name in ('stdout','stderr'):
                shutil.copyfile(src/'wepp/roads/runs'/name,dest/'wepp/roads/runs'/name)
            shutil.copyfile(src/'native-result.json',dest/'native-result.json')
            for name in ('native-result.json','continuation-failure.json'):
                bindings[str(src/name)]=s.h.digest(src/name)
            s.h.save_new(dest/'native-reuse.json',dict(source=str(src),native_result_sha256=s.h.digest(src/'native-result.json'),
                original_outputs=prior['output_sha256'],native_calls=0))
        s.h.save_new(dest/'postprocess-context.json',dict(actual_calendar=calendar,
            source_native_cli_sha256=row['record']['prepared_files']['p1.cli'],
            inherited_stale_calendar_sha256=s.h.digest(src/'climate/site.cli'),
            original_failed_or_unexecuted_root=str(src),native_inputs_changed=False))
        bindings[str(dest/'postprocess-context.json')]=s.h.digest(dest/'postprocess-context.json')
        row['root']=str(dest)
    dependencies.update(bindings)
    d.update(predecessor_sha256=s.h.digest(old),dependencies=dependencies,
        amendment='Preserve old G roots; clone unchanged native inputs to explicitly corrected reader calendar contexts. Reuse exact G native outputs and 40 successful outcomes; execute only six remaining generated contrasts.',
        new_native_calls=6,reused_native_calls=41,postprocess_bindings=bindings)
    s.h.save_new(DECLARATION,d)
    print('Generated continuation declaration',s.h.digest(DECLARATION),flush=True)


def run():
    d=s.seeds.read(DECLARATION)
    review=s.seeds.read(REVIEW)
    assert review['passed'] and review['declaration_sha256']==s.h.digest(DECLARATION)
    s.verify_dependencies(d['dependencies'])
    s.h.save_new(s.ROOT/'generated-continuation-start.json',dict(declaration_sha256=s.h.digest(DECLARATION)))
    results=[]
    for row in d['tasks']:
        root=Path(row['root'])
        if row['context']!='G':
            results.append(s.seeds.read(root/'result.json'))
            continue
        try:
            row['record']=s.seeds.read(root/'native-result.json') if row['arm']=='exact' else s.h.execute(root,row['record'])
            s.h.verify(root,row['record']['output_sha256'])
            diagnostic=s.audit(row)
            climate=s.climate_for(row)
            response=s.h.summarize(root,row['record'],start_year=int(climate['first'][:4]),years=climate['years'])
            result=dict(context=row['context'],arm=row['arm'],root=str(root),diagnostics=diagnostic,response=response)
            s.h.save_new(root/'result.json',result)
            results.append(result)
            s.verify_dependencies(d['dependencies'])
            print(row['context'],row['arm'],response['summary']['sediment_yield_kg'],
                  {k:v for k,v in diagnostic.items() if k.endswith('_pass')},flush=True)
        except Exception as exc:
            # Explicit final continuation boundary, retaining raw and derived failure.
            s.h.save_new(root/'continuation-failure.json',dict(exception=type(exc).__name__,message=str(exc),
                         artifacts=s.h.inventory(root/'wepp/roads')))
            raise
    s.h.save_new(s.ROOT/'results.json',results)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action',choices=('declare','run','analyze'))
    parser.add_argument('--declaration', choices=('declaration-v4.json','declaration-v5.json','declaration-v6.json'),default='declaration-v4.json')
    parser.add_argument('--review', choices=('generated-continuation-review.json','generated-continuation-v6-review.json'),default='generated-continuation-review.json')
    args=parser.parse_args()
    DECLARATION=s.ROOT/args.declaration
    REVIEW=s.ROOT/args.review
    s.DECLARATION=DECLARATION
    {'declare':declare,'run':run,'analyze':s.analyze}[args.action]()
