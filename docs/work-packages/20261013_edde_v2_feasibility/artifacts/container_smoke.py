"""Actual EDDE input -> CLIGEN -> PRISM -> WEPP under the dev container identity."""
import json
import os
from pathlib import Path
import platform
import subprocess
import tarfile
import tempfile

from wepppy.climates.cligen import CligenStationsManager
from wepppy.climates.edde.cligen import build_climate,revise_prism
from wepppy.climates.edde.client import sha256,write_json
import workflows


def main():
    root=Path(tempfile.mkdtemp(prefix='edde-acceptance-'))
    fixture_archive=workflows.OLD/'fixtures.tar.gz'
    expected=json.loads((workflows.OLD/'fixtures-archive.json').read_text())['sha256']
    if sha256(fixture_archive)!=expected:raise ValueError('Fixture archive changed')
    with tarfile.open(fixture_archive) as archive:
        members=[m for m in archive.getmembers() if m.name.startswith('fixtures/apostolic-saw-h1153/')]
        archive.extractall(root,members=members,filter='data')
    workflows.FIXTURES=root/'fixtures'
    sites=json.loads((workflows.OLD/'manifest.json').read_text())['sites']
    site=next(s for s in sites if s['site']=='apostolic-saw-h1153')
    table,meta=workflows.load_series('WRF-MPI','SSP2-4.5',2060,2060,'apostolic-saw-h122')
    point=next(p for p in meta[0]['points'] if p['name']=='apostolic-saw-h122')
    station=CligenStationsManager().get_closest_station((point['longitude'],point['latitude']))
    generated=build_climate(table,meta,station,root/'climate',seed=1001)
    revised=root/'prism.cli'
    revision=revise_prism(root/'climate/wepp.cli',revised,workflows.normal(point['name']),workflows.normal(site['site']))
    results=[]
    for name,path in [('single',root/'climate/wepp.cli'),('prism',revised)]:
        results.append(dict(arm=name,**workflows.execute(site,path,root/name,1)))
    source_files=[workflows.REPO/'wepppy/climates/edde'/f for f in ['client.py','cligen.py','__init__.py','__main__.py']]
    record=dict(status='complete',environment='existing development Compose weppcloud container; no production rollout',
                uid=os.getuid(),gid=os.getgid(),groups=os.getgroups(),platform=platform.platform(),
                umask=next(line.split(':',1)[1].strip() for line in Path('/proc/self/status').read_text().splitlines() if line.startswith('Umask:')),
                git_revision=subprocess.check_output(['git','rev-parse','HEAD'],cwd=workflows.REPO,text=True).strip(),
                source_hashes={str(p.relative_to(workflows.REPO)):sha256(p) for p in source_files},
                fixture_sha256=expected,root=str(root),generation=generated['maximum_source_error'],
                revision=revision,executions=results)
    write_json(workflows.HERE/'container-acceptance.json',record)
    print('Actual EDDE single and PRISM climates passed CLIGEN and WEPP:',root)


if __name__=='__main__':main()
