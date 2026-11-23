"""Count retained catalog keys against a conservative, source-backed naming sample.

Run from the audited repository with the normal and Omni observation JSON paths.
The output contains counts and directory families only. Rules are hypotheses for
the audit, not application configuration. No run directory is opened.
"""
import ast
from collections import Counter, defaultdict
import json
from pathlib import Path
import re
import sys
import subprocess


def literals(module):
    return {n.value for n in ast.walk(ast.parse(module.read_text())) if
            isinstance(n, ast.Constant) and isinstance(n.value, str)}


def naming_inputs():
    interc = Path('wepppy/wepp/interchange')
    mods = list(interc.glob('watershed_*_interchange.py')) + [
        interc / 'hill_interchange.py', interc / 'versioning.py', interc / 'totalwatsed3.py',
        Path('wepppy/wepp/reports/return_periods.py')]
    names = {x for m in mods for x in literals(m)
             if '/' not in x and x.endswith(('.parquet', '.json'))}
    names.update({Path(value).name for value in literals(Path('wepppy/wepp/reports/return_periods.py'))
                  if value.startswith('wepp/output/interchange/') and value.endswith('.parquet')})
    names.update({value for value in literals(interc / 'watershed_interchange.py')
                  if value.endswith('.status.json') and '/' not in value})
    nodb = set()
    files = subprocess.check_output(['git', 'ls-files', '--', 'wepppy/nodb']).decode().splitlines()
    for module in (Path(f) for f in files if f.endswith('.py')):
        classes = [node for node in ast.walk(ast.parse(module.read_bytes())) if isinstance(node, ast.ClassDef)]
        for node in (statement for cls in classes for statement in cls.body):
            if not isinstance(node, (ast.Assign, ast.AnnAssign)):
                continue
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            if (any(isinstance(t, ast.Name) and t.id == 'filename' for t in targets)
                    and isinstance(node.value, ast.Constant) and str(node.value.value).endswith('.nodb')):
                nodb.add(node.value.value)
    wbt = ast.parse(Path('wepppy/topo/wbt/wbt_documentation.py').read_bytes())
    resources = {kw.value.value for n in ast.walk(wbt) if isinstance(n, ast.Call)
                 and isinstance(n.func, ast.Name) and n.func.id == 'ResourceDefinition'
                 for kw in n.keywords if kw.arg == 'filename' and isinstance(kw.value, ast.Constant)}
    return names, nodb, resources


FIXED = {
    'climate/' + name for name in (
        'wepp_cli.parquet', 'ppt.tif', 'tmin.tif', 'tmax.tif',
        'atlas14_intensity_pds_mean_metric.csv', 'wepp_cli_pds_mean_metric.csv')
} | {
    'watershed/hillslopes.parquet', 'watershed/channels.parquet', 'watershed/channels.geojson', 'watershed/flowpaths.parquet',
    'soils/soils.parquet', 'landuse/landuse.parquet', 'wepp/plots/loss.tif', 'wepp/plots/loss.WGS.tif',
    'landuse/nlcd.tif', 'soils/ssurgo.tif', 'watershed/mofe.tif', 'watershed/structure.json',
    'wepp/reports/cache/hillslope_watbal_summary.parquet', 'config-manifest.json',
    'omni/contrasts/contrast_ids.wgs.geojson',
    'omni/scenarios.out.parquet', 'omni/scenarios.channel_summaries.parquet',
    'omni/scenarios.hillslope_summaries.parquet', 'omni/contrasts.out.parquet',
}


def evidence(key, interchange, nodb, resources):
    parts = key.split('/')
    if parts[:2] == ['_pups', 'omni'] and len(parts) > 4 and parts[2] in ('scenarios', 'contrasts'):
        parts = parts[4:]
    key = '/'.join(parts)
    if parts[:-1] == ['dem', 'wbt'] and parts[-1] in resources:
        return 'WBT resource declaration'
    if re.fullmatch(r'wepp/reports/cache/hillslope_watbal_summary\.attempts/[^/]+/(?:native\.parquet|status\.json)', key):
        return 'attempt workspace (policy open)'
    if key == '_query_engine/catalog.json':
        return 'catalog self-reference (policy open)'
    if key in FIXED:
        return 'fixed path'
    if re.fullmatch(r'climate/gridmet_observed_(?:[0-9]+|ws)_[0-9]{4}-[0-9]{4}\.parquet', key):
        return 'writer template'
    if re.fullmatch(r'omni/contrasts/contrast_[0-9]{5,}\.(?:tsv|status\.json)', key):
        return 'writer template'
    if key in nodb:
        return 'controller filename'
    if parts[:-1] == ['wepp','output','interchange'] and parts[-1] in interchange:
        return 'interchange or report source literal'
    return 'unassigned'


def family(key):
    parts = key.split('/')
    if parts[:2] == ['_pups', 'omni'] and len(parts) > 4:
        return '_pups/omni/' + parts[2]
    if len(parts) == 1:
        return '(root files)'
    if len(parts) > 2 and parts[0] in ('wepp', 'export', 'omni', 'dem', 'climate_artifacts'):
        return '/'.join(parts[:2])
    return parts[0]


def main():
    inputs = naming_inputs()
    totals = defaultdict(Counter)
    families = defaultdict(Counter)
    projects = defaultdict(list)
    seen = set()
    catalogs = [v for arg in sys.argv[1:] for v in json.loads(Path(arg).read_bytes()) if 'entries' in v]
    for row in catalogs:
        assert row['root'] not in seen and row['stable']
        seen.add(row['root'])
        kind = row['kind']
        projects[kind].append(len(row['entries']))
        for e in row['entries']:
            k = e['path']
            status = evidence(k, *inputs)
            totals[kind][status] += 1
            families[(family(k), e['extension'], status)][kind] += 1
    projection = []
    for parent in (row for row in catalogs if row['kind'] == 'parent'):
        keys = {e['path'] for e in parent['entries']}
        for kind in ('scenarios', 'contrasts'):
            children = [r for r in catalogs if r['kind'] == kind and r['parent'] == parent['parent']]
            projected = {str(Path(ch['root']).relative_to(parent['root']) / e['path'])
                         for ch in children for e in ch['entries']}
            existing = {k for k in keys if k.startswith('_pups/omni/' + kind + '/')}
            projection.append(dict(parent=parent['parent'], role=kind, child_catalogs=len(children),
                                   projected=len(projected), existing=len(existing),
                                   overlap=len(existing & projected)))
    print(json.dumps(dict(project_counts={k:len(v) for k,v in projects.items()}, totals=totals,
                          projection=projection, families=[dict(family=f, extension=x, evidence=s,
                          counts=c) for (f,x,s),c in sorted(families.items())]),indent=2))


if __name__ == '__main__':
    main()
