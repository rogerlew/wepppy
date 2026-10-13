"""Retain compact, reproducible data and executable-artifact evidence archives."""
from datetime import datetime,timezone
import json
from pathlib import Path
import tarfile

from wepppy.climates.edde.client import sha256,write_json
from workflows import HERE,ROOT


def archive(name,items):
    path=HERE/name
    with tarfile.open(path,'w:gz',compresslevel=6) as out:
        for source,relative in sorted(items,key=lambda pair:pair[1]):
            out.add(source,arcname=relative,recursive=False)
    with tarfile.open(path) as source:members=source.getnames()
    return dict(path=name,sha256=sha256(path),bytes=path.stat().st_size,members=len(members))


def main():
    records=[]
    points=[]
    for directory in ['queries','reference']:
        points.extend((p,str(p.relative_to(HERE))) for p in (HERE/directory).rglob('*') if p.is_file())
    points.extend((p,p.name) for p in HERE.glob('auxiliary-*.csv'))
    records.append(archive('point-data.tar.gz',points))
    climate=[];wepp=[]
    for parent in [ROOT/'workflows-full',ROOT/'canadian-full']:
        for directory in parent.glob('**/climate'):
            climate.extend((p,str(p.relative_to(ROOT))) for p in directory.iterdir() if p.is_file())
        for record in parent.glob('**/execution.json'):
            state=json.loads(record.read_text())
            for name,digest in state['consumed'].items():
                if sha256(record.parent/'runs'/name)!=digest:
                    raise ValueError(f'Consumed artifact changed after execution: {record.parent/name}')
            for name in ['execution.json','stdout.log','stderr.log']:
                p=record.parent/name
                wepp.append((p,str(p.relative_to(ROOT))))
            # Retain exact control, management, soil, slope and ancillary inputs;
            # consumed climate hashes map to the complete generation archive.
            wepp.extend((p,str(p.relative_to(ROOT))) for p in (record.parent/'runs').iterdir()
                        if p.is_file() and p.suffix!='.cli')
    for group in ['apostolic-saw', 'cryptic-beechnut']:
        directory=ROOT/'workflows-pilot-v2/WRF-MPI/Historical'/group/'climate'
        climate.extend((p,str(p.relative_to(ROOT))) for p in directory.iterdir() if p.is_file())
    records.append(archive('generated-climates.tar.gz',climate))
    # Full water-output samples selected by fixed geography/model/arm, not outcome.
    representatives=[ROOT/'workflows-full/WRF-MPI/Historical/apostolic-saw/apostolic-saw-h122/single/output',
                     ROOT/'workflows-full/WRF-MPI/Historical/apostolic-saw/apostolic-saw-h122/prism/output',
                     ROOT/'canadian-full/WRF-MPI/Historical/Toronto/wepp/output']
    for directory in representatives:
        wepp.extend((p,str(p.relative_to(ROOT))) for p in directory.glob('*.wat.dat'))
    records.append(archive('wepp-evidence.tar.gz',wepp))
    write_json(HERE/'evidence-index.json',dict(created_utc=datetime.now(timezone.utc).isoformat(),archives=records,
        native_source_cache=str(ROOT/'cache'),
        source_reproduction='Object keys/ETags/sizes/SHA-256 are in each query manifest inside point-data.tar.gz; full native objects remain in scratch cache, not Git.',
        generated_climate_reproduction='Archive contains raw/normalized daily input, PRN, station parameters, CLIGEN logs, success/failure manifests and successful base/PRISM CLI files.',
        wepp_output_coverage='All 69 full-period runs have exact consumed-input/output hashes, parsed annual water diagnostics and execution results; three fixed full water-output examples retained. Other full outputs remain in scratch and are reproducible from inputs.',
        restore='Extract point-data.tar.gz into this artifacts directory before rerunning study scripts. Extract generated-climates.tar.gz and wepp-evidence.tar.gz into the recorded scratch root to inspect generated/consumed artifacts.'))
    print(records)


if __name__=='__main__':main()
