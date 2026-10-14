"""Compare canonical archive climate members and restored files, including modes."""
import hashlib,json,stat,sys,zipfile
from pathlib import Path
HERE=Path(__file__).resolve().parent
records=[]
for runid in ('edde-ca-20261014','edde-ca-prism-rejected-20261014'):
    root=Path('/wc1/runs/ed')/runid
    archive=next((root/'archives').glob('*.zip'))
    with zipfile.ZipFile(archive) as z:
        names=z.namelist(); print(runid,names[:2])
        members=[]
        for item in z.infolist():
            if not item.filename.startswith('climate/'): continue
            path=root/item.filename
            row={'path':item.filename,'archive_mode':oct(stat.S_IMODE(item.external_attr>>16)),
                 'actual_mode':oct(stat.S_IMODE(path.stat().st_mode))}
            if item.is_dir():
                assert row['archive_mode']==row['actual_mode']
            else:
                row['sha256']=hashlib.sha256(z.read(item)).hexdigest()
                assert row['sha256']==hashlib.sha256(path.read_bytes()).hexdigest()
            members.append(row)
        assert any('source-2060.csv' in m['path'] for m in members)
        assert any('build-status.json' in m['path'] for m in members)
        if 'rejected' in runid:
            statuses=[json.loads(z.read(m['path'])) for m in members if m['path'].endswith('build-status.json')]
            failed=[s for s in statuses if s['state']=='failed'];assert len(failed)==1 and 'PRISM normals are missing' in failed[0]['error']['message']
        records.append({'runid':runid,'archive':archive.name,'members':members,'all_climate_bytes_match':True,'directory_modes_match':True})
(HERE/('archive-after-restore.json' if '--restored' in sys.argv else 'archive-before-restore.json')).write_text(json.dumps(records,indent=2)+'\n')
print([(r['runid'],len(r['members'])) for r in records])
