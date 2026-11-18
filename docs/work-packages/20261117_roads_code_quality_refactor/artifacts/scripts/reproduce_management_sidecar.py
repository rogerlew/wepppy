from pathlib import Path
import os,shutil,runpy,hashlib,json
root=Path('/workdir/wepppy')
out=Path('/tmp/roads-refactor-validation/management-writer-reproduction')
out.mkdir(exist_ok=True)
shutil.copy2(root/'wepppy/wepp/management/scripts/man42_5.man',out/'man42_5.man')
os.chdir(out)
runpy.run_path(str(root/'wepppy/wepp/management/data/UnDisturbed/dump_to_json.py'))
p=out/'man42_5.man.json'
sha=hashlib.sha256(p.read_bytes()).hexdigest()
receipt={'reproduced_sha256':sha,'matches_observed_v5_drift':sha=='9ba3c8e1a9961adcb767f7cd7f32ffa21f66bff8ca909d35892720131261017b','input_sha256':hashlib.sha256((out/'man42_5.man').read_bytes()).hexdigest(),'source_unchanged':hashlib.sha256((root/'wepppy/wepp/management/scripts/man42_5.man.json').read_bytes()).hexdigest()=='c20bdf210f1a10aac0bfbc6a7e13a51e079ee4057d2236d92ac0d397e69911b0'}
(out/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(receipt,indent=2));assert receipt['matches_observed_v5_drift'] and receipt['source_unchanged']
