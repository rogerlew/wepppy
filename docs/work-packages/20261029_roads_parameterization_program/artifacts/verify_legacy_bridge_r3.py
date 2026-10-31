"""Classify failed bridge parity without waiving it; re-audit native outputs."""
from pathlib import Path
import json,struct,shutil
import continuation as c
import legacy_format_bridge_r3 as study
from wepppy.wepp.soils.utils import WeppSoilUtil

WARNING="\n\n *** CAUTION ***\n SOIL FILE FORMAT IS NON-STANDARD WEPP \n User is solely responsible for entering CORRECT \n values for BD, SSC, THETFC, THETDR\n *** CAUTION ***\n"

def bits(x):return struct.unpack('I',struct.pack('f',float(x)))[0]

def main():
    declaration=json.loads((study.ROOT/'declaration.json').read_text());results=json.loads((study.ROOT/'results.json').read_text())
    assert study.sha(study.ROOT/'executed-study.py')==declaration['script_sha256']
    rows=[]
    for r in results['rows']:
        folder=Path(r['folder']);source=Path(r['source']);old=json.loads((source/'record.json').read_text())
        assert study.sha(source/'record.json')==r['source_record_sha256']
        for section,subdir in [('inputs','runs'),('outputs','output')]:
            for n,d in r[section].items():assert study.sha(folder/subdir/n)==d
        current=(folder/'output/H1.loss.dat').read_text();before=(source/'output/H1.loss.dat').read_text()
        assert current.count(WARNING)==1
        warning_only=r['changed_outputs']==['H1.loss.dat'] and current.replace(WARNING,'',1)==before
        diffs=[]
        for diff in r['state_differences']:
            a=diff['before'].split();b=diff['after'].split();assert a[:3]==b[:3]
            diffs.append(dict(stage=a[0],ofe=int(a[1]),layer=int(a[2]),fields=[dict(name=study.probe.FIELDS[i],before=float(x),after=float(y),float32_ulp_distance=abs(bits(x)-bits(y))) for i,(x,y) in enumerate(zip(a[3:],b[3:])) if x!=y]))
        audit_record=dict(case=r['case'],inputs=r['inputs'],outputs=r['outputs'],soil_readback=WeppSoilUtil(str(folder/'runs/p1.sol')).obj['ofes'],width_m=old['width_m'],profile_length_m=old['profile_length_m'],metrics=c.b.parse_loss(folder/'output/H1.loss.dat',old['width_m']))
        # Existing auditor requires an unconsumed reference artifact. Attach it
        # after execution; the consumed-input manifest remains unchanged.
        reference=folder/'runs/reference.sol'
        if not reference.exists():shutil.copy2(source/'runs/p1.sol',reference)
        assert study.sha(reference)==old['inputs']['p1.sol']
        audit=c.audit(folder,r['case'],audit_record)
        rows.append(dict(material=r['material'],native_completed=r['completed'],physical_pass=audit['physical_pass'],audit=audit,
            exact_equivalence_pass=not r['changed_outputs'] and r['initialized_states_equal'],warning_only_difference=warning_only,
            changed_outputs=r['changed_outputs'],initialization_differences=diffs,
            original_export_kg_yr=old['metrics']['sediment_export_kg_yr'],converted_export_kg_yr=audit_record['metrics']['sediment_export_kg_yr']))
    result=dict(cases=len(rows),physical_pass=sum(r['physical_pass'] for r in rows),exact_equivalence_pass=sum(r['exact_equivalence_pass'] for r in rows),
        warning_only_cases=sum(r['warning_only_difference'] for r in rows),rows=rows,
        declaration_sha256=study.sha(study.ROOT/'declaration.json'),results_sha256=study.sha(study.ROOT/'results.json'),script_sha256=study.sha(Path(__file__)),
        disposition='Reject bridge; warning-only classification is diagnostic, not an exception to exact parity. No whole-role substitutions executed.')
    study.dump(study.ROOT/'verification.json',result);study.dump(study.HERE/'legacy-format-bridge-r3-verification.json',result)
    print(json.dumps({k:v for k,v in result.items() if k!='rows'},indent=2))
if __name__=='__main__':main()
