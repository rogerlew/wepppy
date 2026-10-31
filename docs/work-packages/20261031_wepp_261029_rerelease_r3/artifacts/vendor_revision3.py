"""Install the accepted exact pair and complete metadata, with original identity guard."""
from pathlib import Path
import hashlib,json,os,shutil,subprocess
ROOT=Path('/workdir/wepppy');STUDY=ROOT/'out/roads-native-funding-20261031'
NATIVE=Path('/workdir/wepp-forest-release-20261009')
EXPECTED={'wepp_261029':'1d07f5e47692a543e653f449feea23cf298093a9fd664d7a01a1b71dc5e01531','wepp_261029_hill':'568edf8130c33e1d81dc045344cddbfb7106496ef4bda62dfe734d5e1b73b66d'}
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 assert subprocess.check_output(['git','branch','--show-current'],cwd=NATIVE,text=True).strip()=='wepp_260430_negmeltfix_comparator'
 assert subprocess.check_output(['git','symbolic-ref','refs/remotes/origin/HEAD'],cwd=NATIVE,text=True).strip()=='refs/remotes/origin/wepp_260430_negmeltfix_comparator'
 receipt={'artifact_revision':3,'files':{},'deployment':False,'defaults_changed':False}
 pending=[]
 for name,expected in EXPECTED.items():
  binary=NATIVE/'release'/name;meta=json.loads(binary.with_suffix('.json').read_text())
  assert digest(binary)==expected==meta['sha256']
  assert meta['artifact_revision']==3 and meta['source_commit']=='6112b68bce0e21a77f510bde5c24af067a47a647'
  assert meta['matched_pair_sha256']==EXPECTED
  assert 'pending' not in meta['release_status'].lower(),meta['release_status']
  for suffix in ['', '.json']:
   filename=name+suffix;source=NATIVE/'release'/filename;target=ROOT/'wepp_runner/bin'/filename
   original=STUDY/'original-261029-r2/vendored'/filename
   assert digest(target)==digest(original),(filename,'original installed identity changed')
   staged=target.with_name('.'+target.name+'.r3-staged');assert not staged.exists()
   shutil.copy2(source,staged);os.chmod(staged,0o644 if suffix else 0o755)
   assert digest(staged)==digest(source)
   receipt['files'][filename]={'previous_sha256':digest(target),'sha256':digest(staged),'size':staged.stat().st_size}
   pending.append((staged,target))
 # Each complete file replaces atomically; required post-install verification
 # follows before running consumers. Original four-file backup remains retained.
 for staged,target in pending:os.replace(staged,target)
 assert all(digest(ROOT/'wepp_runner/bin'/n)==v['sha256'] for n,v in receipt['files'].items())
 p=ROOT/'docs/work-packages/20261031_wepp_261029_rerelease_r3/artifacts/vendor-revision3.json'
 p.write_text(json.dumps(receipt,indent=2)+'\n');print(p)
if __name__=='__main__':main()
