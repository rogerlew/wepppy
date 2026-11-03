"""Resume 46 unexecuted profiles after explicit abbreviated-LOSS reader repair."""
import argparse
from pathlib import Path

import revised_sensitivity as s

DECLARATION = s.ROOT / 'declaration-v3.json'


def declare():
    old = s.ROOT / 'declaration-v2.json'
    d = s.seeds.read(old)
    first = Path(d['tasks'][0]['root'])
    failure = s.seeds.read(first / 'failure.json')
    assert failure['message'] == 'Incomplete yearly summaries: 0 != 16'
    assert [(r['context'], r['arm']) for r in d['tasks'] if (Path(r['root']) / 'native-result.json').exists()] == [('H', 'baseline')]
    current = s.dependencies()
    changed = {p for p,h in d['dependencies'].items() if p in current and current[p] != h}
    assert changed == {str(Path(s.__file__).resolve())}, changed
    extras = {p:h for p,h in d['dependencies'].items() if p not in current}
    s.verify_dependencies(extras)
    dep = dict(current, **extras)
    dep[str(Path(__file__).resolve())] = s.h.digest(__file__)
    native = s.seeds.read(first / 'native-result.json')
    s.h.verify(first, native['output_sha256'])
    retained = {str(first / name): s.h.digest(first / name) for name in
                ('native-result.json', 'failure.json', 'execution-start.json')}
    retained.update({str(first / name): digest for name,digest in native['output_sha256'].items()})
    dep.update(retained)
    d.update(predecessor_sha256=s.h.digest(old), dependencies=dep,
        amendment='Canonical production LOSS is abbreviated: parse existing mean summary without requiring unrequested yearly text. Calendar audits use actual fixture CLI identity, not normalized research-header identity; full daily/yearly PASS/WAT checks unchanged.',
        retained_failed_attempt=retained, new_native_calls=46, reused_native_calls=1,
        climates={context:s.climate_for(next(r for r in d['tasks'] if r['context']==context)) for context in ('H','L','P','U','G')})
    s.h.save_new(DECLARATION, d)
    print('Continuation declaration', s.h.digest(DECLARATION), flush=True)


def run():
    d = s.seeds.read(DECLARATION)
    review = s.seeds.read(s.ROOT / 'continuation-review.json')
    assert review['passed'] and review['declaration_sha256'] == s.h.digest(DECLARATION)
    s.verify_dependencies(d['dependencies'])
    s.h.save_new(s.ROOT / 'continuation-start.json', dict(declaration_sha256=s.h.digest(DECLARATION)))
    results=[]
    for index,row in enumerate(d['tasks']):
        root=Path(row['root'])
        try:
            row['record'] = s.seeds.read(root / 'native-result.json') if index == 0 else s.h.execute(root,row['record'])
            s.h.verify(root,row['record']['output_sha256'])
            if row['context']=='G' and row['arm']=='exact':
                actual={Path(k).name:v for k,v in row['record']['output_sha256'].items()}
                if actual != row['record']['original_outputs']:
                    raise ValueError('Exact generated control did not reproduce seven outputs')
            diagnostics=s.audit(row)
            climate=s.climate_for(row)
            response=s.h.summarize(root,row['record'],start_year=int(climate['first'][:4]),years=climate['years'])
            result=dict(context=row['context'],arm=row['arm'],root=str(root),diagnostics=diagnostics,response=response)
            s.h.save_new(root/'result.json',result)
            results.append(result)
            s.verify_dependencies(d['dependencies'])
            print(row['context'],row['arm'],response['summary']['sediment_yield_kg'],
                  {k:v for k,v in diagnostics.items() if k.endswith('_pass')},flush=True)
        except Exception as exc:
            # Continuation boundary preserves any further audit failure separately
            # from the first failed reader attempt and never marks it successful.
            s.h.save_new(root/'continuation-failure.json',dict(exception=type(exc).__name__,message=str(exc),
                         artifacts=s.h.inventory(root/'wepp/roads')))
            raise
    s.h.save_new(s.ROOT/'results.json',results)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action',choices=('declare','run','analyze'))
    args=parser.parse_args()
    s.DECLARATION=DECLARATION
    {'declare':declare,'run':run,'analyze':s.analyze}[args.action]()
