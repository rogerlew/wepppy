"""Verify paired study artifacts and render a geographic availability figure."""
import hashlib
import json
from pathlib import Path
import sys

root = Path('/workdir/wepppy')
output = Path(sys.argv[1])
baseline_dir = Path('/tmp/esdac-availability-20261106-baseline')
candidate_dir = Path(sys.argv[2]) if len(sys.argv)>2 else Path('/tmp/esdac-availability-20261106-final')

def load(directory):
    summary = json.loads((directory/'summary.json').read_text())
    records = [json.loads(line) for line in (directory/'results.jsonl').read_text().splitlines()]
    assert len(records) == summary['sample_count'] == 1000
    assert hashlib.sha256((directory/'results.jsonl').read_bytes()).hexdigest() == summary['results_sha256']
    for record in records:
        if 'artifact' in record:
            assert hashlib.sha256((directory/record['artifact']).read_bytes()).hexdigest() == record['sha256']
    return summary, {r['sample_id']:r for r in records}

bs, baseline = load(baseline_dir)
cs, candidate = load(candidate_dir)
assert bs['manifest_sha256'] == cs['manifest_sha256']
assert set(baseline) == set(candidate)
accepted = {'valid', 'degraded'}
recovered, regressions, physical_changes = [], [], []
for ident, old in baseline.items():
    new = candidate[ident]
    if old['outcome'] in accepted:
        if new['outcome'] not in accepted:
            regressions.append(ident)
        else:
            # Soil name is descriptive; all remaining parsed parameters must agree.
            old_physical = {k:v for k,v in old['physical'].items() if k!='slid'}
            new_physical = {k:v for k,v in new['physical'].items() if k!='slid'}
            if old_physical != new_physical:
                physical_changes.append(ident)
    elif new['outcome'] in accepted:
        recovered.append(ident)
consumed_hashes = {name: cs['candidate_sha256'][name] for name in ('esdac/esdac.py','esdac/quality.py')}
assert all(hashlib.sha256((root/'wepppy/eu/soils'/name).read_bytes()).hexdigest()==sha
           for name,sha in consumed_hashes.items())
comparison = dict(baseline_counts=bs['counts'],candidate_counts=cs['counts'],
    recovered_ids=recovered,regression_ids=regressions,physical_change_ids=physical_changes,
    direct_consumed_sources_unchanged=True,direct_consumed_source_sha256=consumed_hashes,
    unused_batch_source_changed_during_direct_study=not cs['source_unchanged'],
    manifest_sha256=cs['manifest_sha256'],bounds=cs['bounds'])
assert not regressions and not physical_changes
(output/'comparison.json').write_text(json.dumps(comparison,indent=2)+'\n')
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
colors = {'valid':'#2166ac','degraded':'#d9a300','rejected':'#b2182b','unexpected_error':'black'}
fig, axes = plt.subplots(1,2,figsize=(13,5),sharex=True,sharey=True)
for ax,records,title in zip(axes,(baseline,candidate),('Previous builder','Revised builder')):
    for outcome,color in colors.items():
        points = [r for r in records.values() if r['outcome']==outcome]
        if points:
            ax.scatter([r['lng'] for r in points],[r['lat'] for r in points],
                s=9,c=color,label=f'{outcome} ({len(points)})',alpha=.8)
    ax.set(title=title,xlabel='Longitude (degrees)')
    ax.grid(alpha=.15)
    ax.legend(loc='lower right',fontsize=8)
axes[0].set_ylabel('Latitude (degrees)')
fig.suptitle('ESDAC availability: same 1,000 stratified valid-anchor cells, seed 20261106')
fig.tight_layout()
fig.savefig(output/'availability.png',dpi=170)
fig.savefig(output/'availability.svg')
print(json.dumps(comparison,indent=2))
