"""Retain completed operational integration, draft review snapshots and archive metadata."""
from pathlib import Path
import hashlib,json,subprocess,tarfile,shutil
ROOT=Path('/workdir/wepppy/out/roads-channel-accounting-20261030')
DEST=Path('/wc1/runs/ro/roads-parameterization-program-20261030/native-accounting-release-integration-v1.tar.gz')
META=ROOT/'retention-integration';META.mkdir(exist_ok=False)
prior={}
manifest={};covered={};excluded={}
parents=[p for p in ROOT.iterdir() if p.is_dir() and (p.name.startswith(('selected-','261029-r2-draft-review','retention-'))) and p != META]
paths=[p for d in parents for p in d.rglob('*') if p.is_file()]
paths += [p for p in ROOT.iterdir() if p.is_file() and p.name != 'archive-release-integration.log']
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
receipt=dict(archive=str(DEST),sha256=sha,bytes=DEST.stat().st_size,files=count,uncompressed_bytes=size,all_members_verified=True,already_retained_files=len(covered),member_manifest_sha256=hashlib.sha256((META/'manifest.json').read_bytes()).hexdigest(),scope='Completed selected runtime/input/output/readback probes, final full-suite and operational logs, draft report review snapshots, archive manifests/receipts and retained failed helper/probe logs. Scientific raw lanes retained in separate verified archives.')
(META/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
for suffix in ['manifest','covered','excluded','receipt']:shutil.copy2(META/(suffix+'.json'),str(DEST)+'.'+suffix+'.json')
print(json.dumps(receipt),flush=True)
