"""Retain immutable raw evidence selections and verify every archive member."""
from pathlib import Path
import argparse,hashlib,json,subprocess,tarfile,shutil
ROOT=Path('/workdir/wepppy/out/roads-parameterization-program-20261031')
DEST=Path('/wc1/runs/ro/roads-parameterization-program-20261031')
HERE=Path(__file__).resolve().parent

def sha(p):
    with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--label',required=True);ap.add_argument('--directory',action='append',required=True);a=ap.parse_args()
    assert '/' not in a.label
    DEST.mkdir(parents=True,exist_ok=True)
    dest=DEST/(a.label+'.tar.gz');assert not dest.exists()
    meta=ROOT/(a.label+'-retention');meta.mkdir(exist_ok=False)
    manifest={};aliases={}
    for name in a.directory:
        root=ROOT/name;assert root.is_dir() and root.resolve().is_relative_to(ROOT.resolve())
        for p in sorted(root.rglob('*')):
            relative=str(p.relative_to(ROOT))
            if p.is_symlink():aliases[relative]=str(p.readlink())
            elif p.is_file():manifest[relative]=sha(p)
    (meta/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n');(meta/'aliases.json').write_text(json.dumps(aliases,indent=2)+'\n');(meta/'files.txt').write_text('\n'.join(manifest)+'\n')
    subprocess.run(['tar','-I','pigz -p 4 -1','-cf',str(dest),'--verbatim-files-from','-T',str(meta/'files.txt')],cwd=ROOT,check=True)
    count=size=0
    with tarfile.open(dest,'r|gz') as archive:
        for member in archive:
            assert member.isfile() and member.name in manifest
            assert hashlib.file_digest(archive.extractfile(member),'sha256').hexdigest()==manifest[member.name]
            count+=1;size+=member.size
    assert count==len(manifest)
    receipt=dict(archive=str(dest),sha256=sha(dest),bytes=dest.stat().st_size,files=count,uncompressed_bytes=size,all_members_verified=True,manifest_sha256=sha(meta/'manifest.json'),omitted_aliases=aliases)
    (HERE/(a.label+'-retention.json')).write_text(json.dumps(receipt,indent=2)+'\n')
    shutil.copy2(HERE/(a.label+'-retention.json'),str(dest)+'.receipt.json');shutil.copy2(meta/'manifest.json',str(dest)+'.manifest.json');shutil.copy2(meta/'aliases.json',str(dest)+'.aliases.json');print(json.dumps(receipt),flush=True)
if __name__=='__main__':main()
