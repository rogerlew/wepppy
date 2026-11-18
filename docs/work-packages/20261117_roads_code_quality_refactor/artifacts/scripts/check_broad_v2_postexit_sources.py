"""Read-only post-exit check; never constructs the interrupted observer."""
import importlib.util,json,hashlib,os,subprocess
from pathlib import Path
root=Path('/workdir/wepppy');out=Path('/tmp/roads-refactor-validation')
script=out/'run_broad_continuation_v2.py'
spec=importlib.util.spec_from_file_location('frozen_broad_v2_source_reader',script)
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
original=out/'broad-continuation-v2-source-before.json';before=json.loads(original.read_text())
after=module.source_manifest();afterfile=out/'broad-continuation-v2-postexit-source-after.json'
assert not afterfile.exists(),'Refuse to overwrite post-exit evidence'
afterfile.write_text(json.dumps(after,indent=2)+'\n')
changed=sorted(k for k in before.keys()|after.keys() if before.get(k)!=after.get(k))
receipt={'checkpoint':subprocess.check_output(['git','rev-parse','HEAD'],cwd=root,text=True).strip(),'environment':{k:os.environ.get(k) for k in module.EXPECTED_ENV},'frozen_observer_sha256':hashlib.sha256(script.read_bytes()).hexdigest(),'before':str(original),'before_sha256':hashlib.sha256(original.read_bytes()).hexdigest(),'after':str(afterfile),'after_sha256':hashlib.sha256(afterfile.read_bytes()).hexdigest(),'before_files':len(before),'after_files':len(after),'changed_paths':changed,'source_unchanged':before==after,'scope':'Fresh process imports only frozen observer definitions and calls source_manifest; no Continuation construction or pytest observer execution.'}
(out/'broad-continuation-v2-postexit-source-receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
print(json.dumps(receipt,indent=2));assert before==after
