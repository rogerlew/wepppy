"""Build isolated matched EROD U1 + DEPEND G1 pair; no release mutation."""
from pathlib import Path
import hashlib,json,shutil,subprocess
SOURCE=Path('/workdir/wepp-forest-release-20261009')
ROOT=Path('/workdir/wepppy/out/roads-parameterization-program-20261031/erod-support-u1')
LABEL='EROD U1 + DEPEND G1'
OVERRIDES={}
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    src=ROOT/'build/src';src.mkdir(parents=True,exist_ok=False)
    manifest={}
    for p in (SOURCE/'src').iterdir():
        if p.is_file() and (p.suffix in ('.for','.f90','.inc','.c') or p.name=='makefile'):
            actual=OVERRIDES.get(p.name,p)
            shutil.copy2(actual,src/p.name);manifest[p.name]=sha(actual)
    for name in ['includes_watershed','includes_hill']:shutil.copytree(SOURCE/'src'/name,src/name)
    shutil.copytree(SOURCE/'fpm-src',ROOT/'build/fpm-src')
    (ROOT/'source.json').write_text(json.dumps(dict(source_base_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=SOURCE,text=True).strip(),files=manifest,source_overrides={n:str(v) for n,v in OVERRIDES.items()},script_sha256=sha(Path(__file__))),indent=2)+'\n')
    with (ROOT/'build.log').open('w') as log:
        for target in ['wepp','wepp_hill','prepare_watershed_includes']:
            subprocess.run(['make','-j4','FC=/usr/bin/gfortran','LINKER=/usr/bin/gfortran',target],cwd=src,env={'PATH':'/usr/bin:/bin'},stdout=log,stderr=subprocess.STDOUT,check=True)
    (ROOT/'bin').mkdir()
    for name in ['wepp','wepp_hill']:shutil.copy2(src/name,ROOT/'bin'/name)
    (ROOT/'build.json').write_text(json.dumps(dict(binaries={n:sha(ROOT/'bin'/n) for n in ['wepp','wepp_hill']},build_log_sha256=sha(ROOT/'build.log'),status='unpromoted '+LABEL+' candidate'),indent=2)+'\n')
    print('Matched isolated candidate ready',flush=True)
if __name__=='__main__':main()
