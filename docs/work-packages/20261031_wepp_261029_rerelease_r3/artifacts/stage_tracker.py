"""Stage only this release's tracker rows; preserve concurrent working edits."""
from pathlib import Path
import subprocess
p=Path('/workdir/wepppy/PROJECT_TRACKER.md');working=p.read_text()
base=subprocess.check_output(['git','show','HEAD:PROJECT_TRACKER.md'],cwd=p.parent,text=True)
road=next(x for x in working.splitlines() if x.startswith('Active: [Roads parameterization'))
release=next(x for x in working.splitlines() if x.startswith('Completed locally: [WEPP 261029 artifact revision 3]'))
old=next(x for x in base.splitlines() if x.startswith('Active: [Roads parameterization'))
new=base.replace(old,release+'\n\n'+road)
blob=subprocess.check_output(['git','hash-object','-w','--stdin'],input=new,text=True,cwd=p.parent).strip()
subprocess.run(['git','update-index','--cacheinfo','100644',blob,'PROJECT_TRACKER.md'],cwd=p.parent,check=True)
