"""Stage a complete matched candidate before any isolated application consumer."""
from pathlib import Path
import subprocess,json,shutil,hashlib,os
ROOT=Path('/workdir/wepppy');DEST=ROOT/'out/261029-r3-isolated';NATIVE=Path('/workdir/wepp-forest-release-20261009');RAW=ROOT/'out/roads-native-funding-20261031'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    source=json.loads((RAW/'D2-frozen-source-manifest.json').read_text())
    for profile in ['includes_watershed','includes_hill']:
        for name in ['pmxelm.inc','pmxhil.inc','pmxpln.inc','pntype.inc']:
            key='src/'+profile+'/'+name;assert sha(NATIVE/key)==source[key]
    pair={n:sha(NATIVE/'release'/n) for n in ['wepp_261029','wepp_261029_hill']}
    pending=[]
    for name,digest in pair.items():
        old=json.loads((ROOT/'wepp_runner/bin'/(name+'.json')).read_text())
        new=json.loads((NATIVE/'release'/(name+'.json')).read_text())
        assert old['features']==new['features'];assert new['sha256']==digest
        assert new['source_commit']=='6112b68bce0e21a77f510bde5c24af067a47a647'
        # Capacity is an enriched release-sidecar field, absent from the native
        # generator. Retain it only after both source capacity profiles match.
        old.update(artifact_revision=3,built_utc=new['built_utc'],sha256=digest,matched_pair_sha256=pair,source_commit=new['source_commit'],source_branch=new['source_branch'],release_status='revision 3 candidate; validation pending; isolated application test only')
        old.pop('validation');old.pop('build');old['known_limitations']=['Isolated candidate; final scientific and release metadata pending.']
        target=DEST/'wepp_runner/bin'/name;stage=target.with_name('.'+name+'.stage');shutil.copy2(NATIVE/'release'/name,stage)
        meta=target.with_suffix('.json');metastage=meta.with_name('.'+meta.name+'.stage');metastage.write_text(json.dumps(old,indent=2)+'\n')
        pending.extend([(stage,target),(metastage,meta)])
    for stage,target in pending:os.replace(stage,target)
    identities={}
    for name,digest in pair.items():
        binary=DEST/'wepp_runner/bin'/name;meta=binary.with_suffix('.json');data=json.loads(meta.read_text())
        assert sha(binary)==data['sha256']==digest and data['matched_pair_sha256']==pair
        identities[name]=dict(binary_sha256=digest,sidecar_sha256=sha(meta))
    for sub in ['node_modules','wepppy/weppcloud/static-src/node_modules']:
        src=ROOT/sub;target=DEST/sub
        if src.exists() and not target.exists():target.symlink_to(src,target_is_directory=True)
    receipt=dict(base_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=DEST,text=True).strip(),detached=True,scope='Committed application base plus final matched native pair and provisional identity/capability sidecars only. Unrelated working-tree changes excluded; final sidecars/publication tested separately.',identities=identities,setup1='Interrupted and excluded: initial staging incorrectly expected generator capacity field; executable/sidecar mismatch correctly rejected by registry. No accepted application count from that attempt.')
    (ROOT/'docs/work-packages/20261031_wepp_261029_rerelease_r3/artifacts/isolated-application-declaration.json').write_text(json.dumps(receipt,indent=2)+'\n')
    print(json.dumps(identities),flush=True)
if __name__=='__main__':main()
