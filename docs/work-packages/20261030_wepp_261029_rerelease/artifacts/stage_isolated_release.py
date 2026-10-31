"""Overlay only release-owned changes onto a detached published-base checkout."""
from pathlib import Path
import hashlib,json,shutil,subprocess
ROOT=Path('/workdir/wepppy');DEST=ROOT/'out/261029-r2-isolated';STUDY=ROOT/'out/roads-channel-accounting-20261030'
PREFIXES=['docs/adrs/ADR-0113-native-roads-boundary-accounting-ablation.md','docs/adrs/ADR-0114-native-equivalent-melt-support-and-storage.md','docs/adrs/ADR-0115-native-boundary-anchored-deposition.md','docs/adrs/ADR-0116-native-channel-sediment-source-accounting.md','docs/adrs/ADR-0117-native-constant-discharge-channel-support.md','docs/adrs/ADR-0118-stable-yalin-transport-capacity.md','docs/adrs/README.md','docs/binary-lifecycle.md','docs/work-packages/20261029_roads_parameterization_program','docs/work-packages/20261030_wepp_261029_rerelease','wepppy/nodb/mods/roads/specification.md','wepp_runner/bin/wepp_261029','wepp_runner/bin/wepp_261029.json','wepp_runner/bin/wepp_261029_hill','wepp_runner/bin/wepp_261029_hill.json','wepppy/weppcloud/routes/usersum/weppcloud/wepp-model.md','wepppy/weppcloud/static/reports/wepp/release-notes/wepp_261029/wepp_261029_release-notes-r2.pdf','wepppy/weppcloud/static/reports/wepp/release-notes/wepp_261029/publication-manifest-r2.json']
def git(*args,cwd=ROOT):return subprocess.check_output(['git',*args],cwd=cwd,text=True).strip()
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 # Both host and container can resolve /workdir; /home/workdir is host-only.
 marker=DEST/'.git';marker.write_text(marker.read_text().replace('/home/workdir/wepppy/','/workdir/wepppy/'))
 gitdir=Path(marker.read_text().strip().removeprefix('gitdir: '))
 backlink=gitdir/'gitdir';backlink.write_text(str(DEST/'.git')+'\n')
 paths=set(git('diff','--name-only','HEAD','--',*PREFIXES).splitlines())
 paths.update(git('ls-files','--others','--exclude-standard','--',*PREFIXES).splitlines());paths.discard('')
 for name in sorted(paths):
  src=ROOT/name;dst=DEST/name;assert src.is_file() and not src.is_symlink(),name
  dst.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(src,dst)
 p=DEST/'PROJECT_TRACKER.md';lines=p.read_text().splitlines()
 for own in (ROOT/'PROJECT_TRACKER.md').read_text().splitlines():
  for token in ['20261030_wepp_261029_rerelease/package.md','20261029_roads_parameterization_program/package.md']:
   if token not in own:continue
   matches=[i for i,l in enumerate(lines) if token in l]
   if matches:lines[matches[0]]=own
   else:
    at=next(i for i,l in enumerate(lines) if '20261029_roads_parameterization_program/package.md' in l)
    lines[at:at]=[own,'']
 p.write_text('\n'.join(lines)+'\n');paths.add('PROJECT_TRACKER.md')
 receipt={'base_commit':git('rev-parse','HEAD',cwd=DEST),'source_checkout_head':git('rev-parse','HEAD'),'detached':git('rev-parse','--abbrev-ref','HEAD',cwd=DEST)=='HEAD','scope':'Only release-owned files plus two owned tracker entries; unrelated committed and uncommitted request-admission changes excluded.','sha256':{n:digest(DEST/n) for n in sorted(paths)},'bootstrap_base_sha256':digest(DEST/'wepppy/weppcloud/routes/bootstrap.py'),'bootstrap_concurrent_sha256':digest(ROOT/'wepppy/weppcloud/routes/bootstrap.py')}
 assert 'parse_json_payload' not in (DEST/'wepppy/weppcloud/routes/bootstrap.py').read_text()
 (STUDY/'isolated-release-overlay.json').write_text(json.dumps(receipt,indent=2)+'\n');print(len(paths),'owned files staged; base',receipt['base_commit'])
if __name__=='__main__':main()
