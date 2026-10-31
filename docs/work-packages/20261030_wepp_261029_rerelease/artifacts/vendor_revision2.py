"""Install the accepted exact pair and complete metadata, with original identity guard."""
from pathlib import Path
import hashlib,json,os,shutil,subprocess
ROOT=Path('/workdir/wepppy');STUDY=ROOT/'out/roads-channel-accounting-20261030'
NATIVE=Path('/workdir/wepp-forest-release-20261009')
EXPECTED={'wepp_261029':'819b91721f67c4a86a5ecea14c5beb840e9a705025da2a2cedf2b97a5e067715','wepp_261029_hill':'21d8480041d2efed942abb8471271ce1a11c5f72190d45c0c42dbe0028c019ed'}
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 assert subprocess.check_output(['git','branch','--show-current'],cwd=NATIVE,text=True).strip()=='wepp_260430_negmeltfix_comparator'
 assert subprocess.check_output(['git','symbolic-ref','refs/remotes/origin/HEAD'],cwd=NATIVE,text=True).strip()=='refs/remotes/origin/wepp_260430_negmeltfix_comparator'
 receipt={'artifact_revision':2,'files':{},'deployment':False,'defaults_changed':False}
 pending=[]
 for name,expected in EXPECTED.items():
  binary=NATIVE/'release'/name;meta=json.loads(binary.with_suffix('.json').read_text())
  assert digest(binary)==expected==meta['sha256']
  assert meta['artifact_revision']==2 and meta['source_commit']=='ba9f2ad91b5165d5cd2954bd64b5df608798541e'
  assert meta['matched_pair_sha256']==EXPECTED
  assert 'pending' not in meta['release_status'].lower(),meta['release_status']
  for suffix in ['', '.json']:
   filename=name+suffix;source=NATIVE/'release'/filename;target=ROOT/'wepp_runner/bin'/filename
   original=STUDY/'original-261029-pair'/filename
   assert digest(target)==digest(original),(filename,'original installed identity changed')
   staged=target.with_name('.'+target.name+'.r2-staged');assert not staged.exists()
   shutil.copy2(source,staged);os.chmod(staged,0o644 if suffix else 0o755)
   assert digest(staged)==digest(source)
   receipt['files'][filename]={'previous_sha256':digest(target),'sha256':digest(staged),'size':staged.stat().st_size}
   pending.append((staged,target))
 # Each complete file replaces atomically; required post-install verification
 # follows before running consumers. Original four-file backup remains retained.
 for staged,target in pending:os.replace(staged,target)
 assert all(digest(ROOT/'wepp_runner/bin'/n)==v['sha256'] for n,v in receipt['files'].items())
 p=ROOT/'docs/work-packages/20261030_wepp_261029_rerelease/artifacts/vendor-revision2.json'
 p.write_text(json.dumps(receipt,indent=2)+'\n');print(p)
if __name__=='__main__':main()
