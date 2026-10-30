"""Host-side staging of scientific fswepp2 reference assets for container runs."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess


def stage(source,root):
    root.mkdir(parents=True,exist_ok=False)
    paths=list((source/'api/db/wepproad').rglob('*.sol'))
    paths+=list((source/'api/db/wepproad').rglob('*.man'))
    for case in ('default','run_2','run_3','run_4','run_5'):
        for extension in ('in','sol','slp','cli','out'):
            matches=list((source/'parity-runs/wepproad'/case/'legacy/working').glob(f'*.{extension}'))
            if len(matches)!=1:
                raise ValueError(f'Expected one {extension} for {case}')
            paths.extend(matches)
    identity={}
    for p in paths:
        relative=p.relative_to(source)
        target=root/'reference'/relative
        target.parent.mkdir(parents=True,exist_ok=True)
        shutil.copy2(p,target)
        identity[str(relative)]=hashlib.sha256(p.read_bytes()).hexdigest()
    target=root/'reference/bin/wepp2010'
    target.parent.mkdir(parents=True)
    shutil.copy2(source/'api/wepp/bin/wepp2010',target)
    identity['api/wepp/bin/wepp2010']=hashlib.sha256(target.read_bytes()).hexdigest()
    commit=subprocess.check_output(['git','-C',str(source),'rev-parse','HEAD'],text=True).strip()
    (root/'reference-source.json').write_text(json.dumps(dict(source=str(source),commit=commit,sha256=identity),indent=2)+'\n')
    print(root)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--fswepp2',type=Path,default=Path('/workdir/fswepp2'))
    p.add_argument('--root',type=Path,required=True)
    args=p.parse_args()
    stage(args.fswepp2,args.root)
