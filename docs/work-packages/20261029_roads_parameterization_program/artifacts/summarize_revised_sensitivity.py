"""Reproduce compact sensitivity evidence from already validated native receipts."""
from decimal import Decimal
from pathlib import Path
import json
import hashlib

ROOT=Path('/wc1/runs/ro/roads-parameterization-program-20261103/revised-sensitivity-v1')
HERE=Path(__file__).resolve().parent


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    results=json.loads((ROOT/'results.json').read_text())
    analysis=json.loads((ROOT/'analysis.json').read_text())
    assert len(results)==analysis['planned']==analysis['completed']==47
    assert all(analysis[k] for k in ('all_physical_checks_pass','all_calendar_checks_pass','all_strict_particle_checks_pass'))
    rows=[]
    bindings={str(ROOT/name):sha(ROOT/name) for name in ('declaration-v6.json','results.json','analysis.json')}
    for result in results:
        root=Path(result['root'])
        audit=json.loads((root/'audits.json').read_text())
        native=json.loads((root/'wepp/roads/record.json').read_text())
        bindings[str(root/'audits.json')]=sha(root/'audits.json')
        bindings[str(root/'wepp/roads/record.json')]=sha(root/'wepp/roads/record.json')
        width=Decimal(str(native['width_m']));years=Decimal(native['metrics']['years'])
        non_event=audit['completeness']['positive_terminal_non_event_dates']
        missing_mass=sum(Decimal(r['sedleave_kg_m_token'].replace('D','E')) for r in non_event)*width/years
        rows.append(dict(context=result['context'],arm=result['arm'],
            **{k:result['response']['summary'][k] for k in ('sediment_yield_kg','runoff_volume_m3','modeled_area_m2','sediment_yield_density_kg_m2')},
            loss_export_kg_yr=native['metrics']['sediment_export_kg_yr'],
            element_terminal_kg_yr=audit['physical']['sediment']['ofes'][-1]['boundary_kg_yr'],
            positive_non_event_days=len(non_event),non_event_element_kg_yr=float(missing_mass)))
    value=dict(source_sha256=bindings,reporter_sha256=sha(__file__),rows=rows,
        native_calls=47,prepared_alias_probes=12,distinct_input_signatures=analysis['distinct_input_signatures'],
        interactions=analysis['interactions'],aliases=analysis['aliases'],
        changed_day_range=[min(p['event_response']['changed_days'] for p in analysis['pairs'] if p['arm']!='baseline'),
                           max(p['event_response']['changed_days'] for p in analysis['pairs'] if p['arm']!='baseline')],
        source_versions='Native calls occurred under declarations v2, v3 and v6; final guard retrospectively admitted all47 contexts.',
        field_calibration=False,default_adoption=False,withheld_materials_used=False)
    target=HERE/'revised-sensitivity-summary.json'
    with target.open('x') as stream: json.dump(value,stream,indent=2,sort_keys=True,allow_nan=False);stream.write('\n')
    print(target)


if __name__=='__main__': main()
