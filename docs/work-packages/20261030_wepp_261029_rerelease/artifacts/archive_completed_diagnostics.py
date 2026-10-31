"""Retain completed diagnostic evidence missing from the earlier controls archive."""
from pathlib import Path
import hashlib,json,subprocess,tarfile,shutil
ROOT=Path('/workdir/wepppy/out/roads-channel-accounting-20261030')
DEST=Path('/wc1/runs/ro/roads-parameterization-program-20261030/native-accounting-channel-diagnostics-v1.tar.gz')
META=ROOT/'retention-diagnostics';META.mkdir(exist_ok=False)
prior=json.loads((ROOT/'retention-controls/manifest.json').read_text())
manifest={};covered={};excluded={}
parents=[p for p in ROOT.iterdir() if p.is_dir() and ('U10' not in p.name) and not p.name.startswith(('retention-','selected-','261029-r2-draft'))]
paths=[p for d in parents for p in d.rglob('*') if p.is_file()]
paths += [p for p in ROOT.iterdir() if p.is_file() and p.name.startswith(('261029-r2-','U9a-','U9-','U7-','cedar-U9','cedar-U7','finish-cedar-U9','finish-cedar-U7','finish-cedar-261029','disturbed-261029','replay_261029','finish_cedar_r2','archive_completed_diagnostics'))]
for p in sorted(set(paths)):
 rel=str(p.relative_to(ROOT));parts=p.relative_to(ROOT).parts
 if len(parts) > 1 and parts[0].startswith('disturbed-') and parts[1]!='disturbed_matrix0':
  excluded[rel]='Non-scientific pytest temporary path';continue
 assert not p.is_symlink(),p
 with p.open('rb') as f:digest=hashlib.file_digest(f,'sha256').hexdigest()
 if prior.get(rel)==digest:covered[rel]=digest
 else:manifest[rel]=digest
for name,value in [('manifest',manifest),('covered',covered),('excluded',excluded)]:
 (META/(name+'.json')).write_text(json.dumps(value,indent=2)+'\n')
(META/'files.txt').write_text('\n'.join(manifest)+'\n')
assert not DEST.exists()
print('Frozen',len(manifest),'new files;',len(covered),'already retained',flush=True)
subprocess.run(['tar','-I','pigz -p 4 -1','-cf',str(DEST),'--verbatim-files-from','-T',str(META/'files.txt')],cwd=ROOT,check=True)
count=size=0
with tarfile.open(DEST,'r|gz') as tar:
 for member in tar:
  assert member.isfile() and member.name in manifest
  assert hashlib.file_digest(tar.extractfile(member),'sha256').hexdigest()==manifest[member.name],member.name
  count+=1;size+=member.size
assert count==len(manifest)
with DEST.open('rb') as f:sha=hashlib.file_digest(f,'sha256').hexdigest()
receipt=dict(archive=str(DEST),sha256=sha,bytes=DEST.stat().st_size,files=count,uncompressed_bytes=size,all_members_verified=True,already_retained_files=len(covered),prior_archive='native-accounting-channel-controls-v1.tar.gz',member_manifest_sha256=hashlib.sha256((META/'manifest.json').read_bytes()).hexdigest(),scope='Completed pre-U10 diagnostics including matched U9a and system Cedar, independent causal observations and retained original pairs; excludes active U10 and release integration.')
(META/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
for suffix in ['manifest','covered','excluded','receipt']:shutil.copy2(META/(suffix+'.json'),str(DEST)+'.'+suffix+'.json')
print(json.dumps(receipt),flush=True)
