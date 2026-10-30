"""Retain compact, complete comparisons and generate a scientific study report."""
from __future__ import annotations
import csv
import hashlib
import json
from pathlib import Path
import shutil

HERE=Path(__file__).resolve().parent
ROOT=Path('/wc1/runs/ro/roads-drainage-validation-20261029-v2')


def table(headers,rows):
    return '\n'.join(['| '+' | '.join(headers)+' |','| '+' | '.join('---' for _ in headers)+' |',
        *['| '+' | '.join(str(v) for v in row)+' |' for row in rows]])


def main():
    analysis=ROOT/'analysis-v1';runtime=ROOT/'runtime-bridge-v1/analysis-v3'
    summary=json.loads((analysis/'summary.json').read_text())
    bridge=json.loads((runtime/'summary.json').read_text())
    rows=json.loads((analysis/'comparisons.json').read_text())
    mode_rows=json.loads((runtime/'comparisons.json').read_text())
    dest=HERE
    for source,name in [(analysis/'summary.json','summary.json'),(analysis/'comparisons.csv','comparisons.csv'),
        (analysis/'native-audits.csv','native-audits.csv'),(analysis/'pair-effects.csv','pair-effects.csv'),
        (analysis/'provenance.json','reader-provenance.json'),(runtime/'summary.json','runtime-summary.json'),
        (runtime/'comparisons.csv','runtime-comparisons.csv'),(runtime/'pair-effects.csv','runtime-pair-effects.csv'),
        (runtime/'exact-input-alias-comparisons.csv','runtime-exact-input-alias-comparisons.csv'),
        (runtime/'provenance.json','runtime-analysis-provenance.json'),
        (ROOT/'runtime-bridge-v1/declaration.json','runtime-declaration.json')]:
        shutil.copy2(source,dest/name)
    # Large native/event tables remain in scratch; retain their hashes and exact locations.
    evidence={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in [
        analysis/'results.json',analysis/'reference-provenance.json',analysis/'control-reproduction.json',analysis/'input-aliases.json',
        runtime/'results.json',ROOT/'frozen-package.md',ROOT/'frozen-study_execplan.md']}
    (dest/'large-artifact-manifest.json').write_text(json.dumps(evidence,indent=2)+'\n')
    overall=[]
    for t in ('current','source','policy'):
        g=summary['strata']['all'][t+':all']
        overall.append([t,f"{g['within']}/{g['positive']}",g['above'],g['below'],f"{g['zero_matches']}/{g['zeros']}",f"{g['median_ratio']:.3g}"])
    soils=[]
    for soil in ('sand','loam','silt','clay','holdout','new_lithic','new_lowk','new_open'):
        gs=[summary['strata']['soil'][t+':'+soil] for t in ('current','source','policy')]
        soils.append([soil,*[f"{g['within']}/{g['positive']}" for g in gs],f"{gs[1]['min_ratio']:.3g}–{gs[1]['max_ratio']:.3g}"])
    climates=[]
    for climate in ('birmingham','denver','flagstaff','charleston','site'):
        gs=[summary['strata']['climate'][t+':'+climate] for t in ('current','source','policy')]
        climates.append([climate,*[f"{g['within']}/{g['positive']}" for g in gs]])
    modes=[]
    for runtime_name in ('ui-only','site-shared'):
        for t in ('current','source','policy'):
            g=bridge[runtime_name+':'+t]
            modes.append([runtime_name,t,f"{g['within']}/{g['positive']}",g['above'],g['below'],f"{g['report_reconciled']}/{g['cases']}"])
    selected=[]
    for soil in ('sand','clay','new_lithic','new_lowk','new_open'):
        base=[r for r in rows if r['soil']==soil and r['climate']=='site' and r['design']=='outunrut' and r['surface']=='gravel' and r['traffic']=='high' and r['treatment'] in ('current','source')]
        for r in base:selected.append([soil,'no UI',r['treatment'],f"{r['export_kg_yr']:.2f}",f"{r['ratio']:.3g}" if r['ratio'] is not None else 'zero reference',f"{r['buffer_dp_m3_yr']:.1f}",r['near_capacity_days']])
        for r in mode_rows:
            if r['soil']==soil and r['climate']=='site' and r['design']=='outunrut':
                selected.append([soil,r['runtime'],r['drainage'],f"{r['export_kg_yr']:.2f}",f"{r['ratio']:.3g}" if r['ratio'] is not None else 'zero reference',f"{r['buffer_dp_m3_yr']:.1f}",r['near_capacity_days']])
    worst=sorted((r for r in rows if r['treatment']=='source' and r['ratio'] is not None),key=lambda r:abs(__import__('math').log10(max(r['ratio'],1e-300))),reverse=True)[:12]
    worst_table=table(['Profile','Source kg/yr','WEPP2010 kg/yr','Ratio'],[[r['profile'],f"{r['export_kg_yr']:.3f}",f"{r['legacy_kg_yr']:.3f}",f"{r['ratio']:.4g}"] for r in worst])
    report=f'''# Roads drainage validation results

Completed native execution: 1,920 paired-matrix runs plus 192 runtime-bridge runs.
**The proposed conductivity change does not generalize well enough to adopt.**
In the simplified matrix it fixes 17 factor-ten failures but introduces 13, changing
coverage from 820/905 to 824/905. The conservative policy falls to 814/905. In the
UI-mode bridge, current and source treatments both pass 61/71 positive references;
with the site's shared settings both pass 14/16. No production candidate is accepted.

## Principal finding: runtime mode is part of parameterization

The earlier simplified studies and this frozen broad matrix omit `wepp_ui.txt`.
The actual Roads workspace copies it from baseline projects; both source projects
and the canonical Roads fixture contain it. Its presence activates a different
water-balance path. Therefore improvements in the simplified matrix cannot be
presented as production-mode validation. The bridge explicitly activates and audits
that mode, then tests the site shared-file bundle. See
[physical justification](physical-justification.md) for equations, source audit,
soil classes and primary literature.

## Frozen design and acceptance

Eight labels (seven distinct material profiles), five climates, four designs,
two surfaces and three traffic levels give 960 paired profiles. Each uses 16 complete
years, exact `wepp_261026`, bare/bare/forest role preparation and normalized 200 mm
boundaries. Only buffer lower-boundary conductivity changes. The source alternative
uses source restriction conductivity without /1000 scaling, or deepest emitted Ksat
where no restriction was identified. The policy view retains current lithic values
and selects the source alternative otherwise. Policy rows reuse runs.

Three newly tested profiles are lithic 1856573, mineral-horizon 53949 and unrestricted
1718494. Old loam/holdout have identical horizon/restriction properties and are not
independent validation samples. All specimens come from two existing projects;
climate swaps are stress tests, not geographic field validation.

A positive-reference export passes at 0.1–10× WEPP2010. Every failure and exact-zero
reference is retained; no epsilon denominator or fitted acceptance threshold.
Physical acceptance requires evidence beyond compatibility. Neither source nor
policy satisfies the complete acceptance contract.

## Broad matrix: common-report sediment export

{table(['Treatment','Within factor ten','Above 10×','Below 0.1×','Zero matches/references','Median ratio'],overall)}

Reference denominators are positive common native report exports. Reused legacy
references are rehashed and matched by climate, texture, design, surface and traffic.
Modern-binary legacy-soil reference: {summary['modern_legacy_reference']['within']}/{summary['modern_legacy_reference']['positive']} positive comparisons within factor ten.

{table(['Soil label','Current','Source','Policy','Source ratio range'],soils)}

{table(['Climate','Current','Source','Policy'],climates)}

Removing the duplicate `holdout` leaves {summary['excluding_duplicate_holdout']['source']['cases']} profile comparisons:
current {summary['excluding_duplicate_holdout']['current']['within']}/{summary['excluding_duplicate_holdout']['current']['positive']},
source {summary['excluding_duplicate_holdout']['source']['within']}/{summary['excluding_duplicate_holdout']['source']['positive']},
policy {summary['excluding_duplicate_holdout']['policy']['within']}/{summary['excluding_duplicate_holdout']['policy']['positive']} within factor ten.

Transitions from current to source: `{summary['transitions']['source']}`.
Transitions from current to policy: `{summary['transitions']['policy']}`.
`True` denotes within factor ten, `False` a positive-reference failure, and `None`
an exact-zero reference. Complete strata and all failures are retained in
[summary](artifacts/summary.json) and [comparison CSV](artifacts/comparisons.csv).

### Largest source-scenario departures

{worst_table}

## Runtime bridge

Before any bridge outcomes, freeze gravel/high traffic and both rutted/unrutted
geometries for all eight soil labels and five climates: 160 runs adding only
`wepp_ui.txt`. Another 32 site-climate runs copy all seven canonical Roads shared
files unchanged. Actual input hashes, mode banners and matching baseline soils are
verified. This is a controlled runtime bridge, not a full-project replay or a
revalidation of every paved/traffic combination under production settings.

{table(['Runtime','Treatment','Within factor ten','Above 10×','Below 0.1×','Report/ELEMENT reconciled'],modes)}

For site sand, unrutted gravel/high, current-drainage export changes from
897.41 kg/year without UI to 147.98 kg/year with UI alone, and 165.27 kg/year with
the shared site settings. Under the shared settings, source drainage gives
53.02 kg/year. Current-drainage buffer lateral outflow rises from approximately
607 m³/year without UI to 2,736 m³/year with UI alone; its deep percolation actually
falls from 30.5 to 15.1 m³/year. The mode effect therefore cannot be described as
simply increasing deep drainage. Source drainage then shifts much of the UI-mode
lateral flow to deep percolation.

The site bundle includes snow, evaporation and groundwater settings, so its contrast
with UI-only is not attributable solely to deep percolation. Other climates do not
receive transplanted site-specific settings. Complete rows:
[runtime comparisons](artifacts/runtime-comparisons.csv). Exact matches of all
common consumed-input hashes also permit comparing these outputs to the remaining
paved/gravel and high/low labels that share those bytes. These derived comparisons
are retained in [runtime input aliases](artifacts/runtime-exact-input-alias-comparisons.csv);
they are not additional simulations or independently differentiated surface responses.

### Site unrutted gravel/high diagnostic panel

{table(['Soil','Runtime','Drainage','Export kg/yr','Ratio to legacy','Buffer Dp m³/yr','Near-capacity days'],selected)}

Near-capacity means reported soil water at least 90% of reported porosity capacity;
the denominator is 5,844 days. Dp is deep percolation from the buffer only. Runoff
boundaries use cumulative contributing area, while lateral transfers use local OFE
area. Apparent storage residuals are not claimed as full water closure. Year-one
sensitivity is retained as years 2–16 export and water summaries in the raw analysis.

## Artifact and accounting validation

All {summary['native_cases']} broad cases have successful native completion and complete finite daily
water calendars. {summary['prior_controls_exact']}/{summary['prior_controls']} prior role controls reproduce all seven native outputs exactly.
There are {summary['unique_consumed_input_signatures']} distinct consumed byte signatures and
{summary['unique_semantic_input_signatures']} semantic signatures after excluding soil labels/header metadata.
Paved/gravel, high/low traffic and some inbare/inveg modern inputs alias; these
scenarios are compatibility labels, not independent physically differentiated tests.

The broad matrix contains **{summary['negative_sediment_cases']} cases with {summary['negative_sediment_flux_records']} negative native sediment-flux records**.
These are invalid physical budgets even if their signed sums happen to match report
precision. They are neither clipped to zero nor accepted as reconciled. One
Flagstaff/new_lithic/no-traffic source case emits −8.436 kg/m at the fill boundary
and −8.420 kg/m at the buffer boundary on year 7, day 251. Its annual report export
for that year is zero; report agreement alone would miss the invalid boundary flux.
The runtime bridge uses high traffic, so it does not establish whether this failure
persists in UI-mode no-traffic cases. All 12 flagged records are retained in
[negative sediment events](artifacts/negative-sediment-events.csv).

ELEMENT/report reconciliation passes {summary['sediment_report_reconciled']}/{summary['native_cases']} broad cases;
{summary['ebe_mismatch_cases']} cases have {summary['ebe_mismatch_events']} EBE/ELEMENT event mismatches.
These are retained with original source-precision bounds in
[native audits](artifacts/native-audits.csv). No tolerances were widened. Net OFE
sediment exchange is not gross detachment or attribution of particles to their origin.
Upstream input equality does not guarantee output equality; the native coupled
runoff/erosion behavior is retained in [pair effects](artifacts/pair-effects.csv).

Raw artifacts: `{ROOT}`. Frozen declarations, binary/source hashes, reader provenance
and portable comparisons are in `artifacts/`; large retained tables and prior control
hashes are indexed by [manifest](artifacts/large-artifact-manifest.json).
Failed staging attempts contained no new model outcomes and remain retained.

## Recommendation and limits

Do not change production `kslast` from this study. First use actual project runtime
settings for any subsequent Roads parameterization comparison, and preserve those
settings in the input manifest. The next bounded experiment should also reproduce
the Flagstaff/new_lithic/no-traffic negative flux with and without UI mode before
using that configuration's annual sediment report for parameter fitting. Its current
known failure is confined to the simplified study; this package does not establish
a production defect. Distinguish lithic bedrock, low-conductivity mineral
horizons and missing restriction information. A universal /1000 removal or deepest
horizon substitution is not physically established.

The assumed underlying thickness, generated depth rounding, native 1.8 m cap, and
missing local geological/hydrologic observations remain unresolved. For silt, the
source endpoint is taken from an emitted horizon below the computational cap, so it
is not a literal no-throttle boundary. Keep the 200 mm normalization. Any future
production rule requires a parameterization ADR and writer/consumer validation.

Validation gates and final review are recorded in [validation](artifacts/validation.md).
'''
    (HERE.parent/'report.md').write_text(report)
    print('Published portable evidence and report')


if __name__=='__main__':main()
