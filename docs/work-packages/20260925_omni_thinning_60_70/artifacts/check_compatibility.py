from pathlib import Path
import subprocess,json,hashlib,csv,io
base='cf6437095fead72722f91ccc124119c7f824d65e'
root=Path('wepppy/wepp/management/data')
report={'base':base,'catalogs':{},'legacy_assets':{},'new_assets':{}}
def old(p): return subprocess.check_output(['git','show',f'{base}:{p}'])
for name in ('disturbed','c3s-disturbed','au-disturbed','eu-corine-disturbed','revegetation'):
 p=root/f'{name}.json'; before=json.loads(old(p)); after=json.loads(p.read_bytes())
 assert all(after[k]==v for k,v in before.items())
 added={k:v for k,v in after.items() if k not in before}
 assert len(added)==8
 assert {v['DisturbedClass'] for v in added.values()}=={f'thinning_{c}_{g}' for c in (60,70) for g in (75,85,90,93)}
 report['catalogs'][name]={'old_entries_unchanged':len(before),'added':{k:v['DisturbedClass'] for k,v in added.items()}}
for c in (30,40,50,65):
 for g in (75,85,90,93):
  p=root/f'UnDisturbed/Thinning_{c}_{g}.man'; assert old(p)==p.read_bytes(); report['legacy_assets'][p.name]=hashlib.sha256(p.read_bytes()).hexdigest()
for c in (60,70):
 for g in (75,85,90,93):
  p=root/f'UnDisturbed/Thinning_{c}_{g}.man'; source=(root/f'UnDisturbed/Thinning_40_{g}.man').read_bytes()
  assert p.read_bytes().replace(f'1.10000 {c/100:.5f} 330 1000'.encode(),b'1.10000 0.40000 330 1000')==source
  report['new_assets'][p.name]={'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'only_initial_canopy_differs':True}
p=Path('wepppy/wepp/management/scripts/disturbed_weppcloud_managements.csv'); b=old(p); a=p.read_bytes(); assert a.startswith(b)
rows=list(csv.DictReader(io.StringIO(a.decode()))); new=[r for r in rows if int(r['key']) in range(151,159)]; assert len(new)==8
for r in new:
 _,c,g=r['disturbed_class'].split('_'); assert float(r['ini.cancov'])==int(c)/100; assert float(r['ini.inrcov'])==float(r['ini.rilcov'])==int(g)/100
report['csv']={'all_existing_bytes_preserved':True,'added_rows':len(new)}
report['result']='PASS'
print(json.dumps(report,indent=2))
