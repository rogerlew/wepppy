"""Observe the pinned export gate; require exact native parity before explaining it.

Host-only debugger uses snapshotted container loader/libraries. This is diagnostic
instrumentation, never a correction to model outputs or parameter acceptance.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess

BASE=Path('/wc1/runs/ro/roads-parameterization-program-20261029')
BINARY=Path('/workdir/wepppy/wepp_runner/bin/wepp_261026')
BINARY_SHA='a6351d371030f702be5eb0d727d8e7181eeb9d60e9ddf6ce05d9616e5d759d48'
SOURCE=BASE/'report-trace-v7/source'
LIBS=BASE/'container-runtime'
HERE=Path(__file__).resolve().parent


def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def dump(path,value):path.write_text(json.dumps(value,indent=2,allow_nan=False)+'\n')


def trace(folder,destination):
    folder=folder.resolve();destination=destination.resolve()
    record=json.loads((folder/'record.json').read_text())
    if record['status']!='completed':raise ValueError('Requires completed native case')
    if digest(BINARY)!=BINARY_SHA:raise ValueError('Trace symbols require pinned binary')
    library_hashes=json.loads((LIBS/'manifest.json').read_text())
    for name,sha in library_hashes.items():
        if digest(LIBS/name)!=sha:raise ValueError('Container runtime drift')
    frozen=json.loads((BASE/'report-trace-v7/verification.json').read_text())
    for name,sha in frozen['source_sha256'].items():
        if digest(SOURCE/name)!=sha:raise ValueError('Pinned source drift')
    for sub,key in (('runs','inputs'),('output','outputs')):
        for name,sha in record[key].items():
            if digest(folder/sub/name)!=sha:raise ValueError('Source artifact drift')
    destination.mkdir(parents=True,exist_ok=False)
    runs=destination/'runs';out=destination/'output';runs.mkdir();out.mkdir()
    for name in record['inputs']:shutil.copy2(folder/'runs'/name,runs/name)
    shutil.copytree(SOURCE,destination/'source')
    script=f'''set pagination off
set confirm off
set debuginfod enabled off
set substitute-path /home/workdir/wepp-forest-release-20261009/src {destination}/source
set stop-on-solib-events 1
run --library-path {LIBS} {BINARY} < p1.run > native.stdout 2> native.stderr
add-symbol-file {BINARY} 0x402370
set stop-on-solib-events 0
set language fortran
break sloss.for:275 if iplane == 3 .and. ofelod(3) > 0 .and. qout <= 0
commands
silent
printf "TRACE qout=%.9g load=%.9g export=%.9g plane=%d\\n", qout, ofelod(3), avsole, iplane
up
printf "DATE year=%d sdate=%d day=%d mon=%d\\n", lyear,sdate,day,mon
down
continue
end
continue
'''
    (destination/'trace.gdb').write_text(script)
    declaration=dict(source_case=str(folder),record_sha256=digest(folder/'record.json'),
        binary_sha256=BINARY_SHA,source_commit=frozen['source_commit'],source_sha256=frozen['source_sha256'],
        runtime_libraries=library_hashes,script_sha256=digest(Path(__file__)),gdb_script_sha256=digest(destination/'trace.gdb'),
        scope='Three noncontoured OFEs, pinned binary only; observe qout export branch without changing output or precision bounds')
    dump(destination/'declaration.json',declaration)
    with (destination/'debugger.log').open('w') as log:
        proc=subprocess.run(['gdb','-q','-batch','-x',str(destination/'trace.gdb'),str(LIBS/'ld-linux-x86-64.so.2')],
                            cwd=runs,stdout=log,stderr=subprocess.STDOUT,timeout=180)
    log=(destination/'debugger.log').read_text()
    if proc.returncode or 'exited normally' not in log or 'Error in testing condition' in log:
        raise ValueError('Debugger observation failed; retained scratch is not evidence')
    parity={name:digest(out/name)==sha for name,sha in record['outputs'].items()}
    if not all(parity.values()):raise ValueError('Debugger/native runtime parity failed')
    pattern=r'TRACE qout=([^ ]+) load=([^ ]+) export=([^ ]+) plane=(\d+).*?DATE year=(\d+) sdate=(\d+)'
    events=[dict(qout=float(q),ofelod_kg_m=float(load),avsole_kg_m=float(export),ofe=int(ofe),year=int(year),julian=int(day))
            for q,load,export,ofe,year,day in re.findall(pattern,log,re.S)]
    if len(events)!=log.count('TRACE ') or len({(e['year'],e['julian']) for e in events})!=len(events):
        raise ValueError('Incomplete or duplicate debugger event capture')
    audit_file=folder.parents[1]/'analysis/cases'/f"{record['name']}.json"
    audit=json.loads(audit_file.read_text())
    if audit['record_sha256']!=digest(folder/'record.json'):raise ValueError('Prior native audit drift')
    budget=audit['sediment']
    explained=sum(e['ofelod_kg_m']-e['avsole_kg_m'] for e in events)*record['width_m']/16
    residual=budget['report_delta_kg_yr']-explained
    by_date={(e['year'],e['julian']):e for e in events}
    unresolved=[]
    for mismatch in audit['ebe']['mismatches']:
        event=by_date.get(tuple(mismatch['date']))
        if event is None or abs(mismatch['element_kg_m']-event['ofelod_kg_m'])>.00051 or abs(mismatch['ebe_kg_m']-event['avsole_kg_m'])>.05001:
            unresolved.append(mismatch)
    result=dict(declaration=declaration,outputs_byte_identical=parity,events=events,
        native_audit_sha256=digest(audit_file),debugger_log_sha256=digest(destination/'debugger.log'),
        original_report_delta_kg_yr=budget['report_delta_kg_yr'],explained_kg_yr=explained,
        residual_kg_yr=residual,unchanged_precision_bound_kg_yr=budget['report_bound_kg_yr'],
        unresolved_ebe_mismatches=unresolved,
        source_explained=(not budget['negative_fluxes'] and not unresolved and abs(residual)<=budget['report_bound_kg_yr']),
        scope='Case-specific export-gate explanation only. Original loads/flags unchanged; no parameter or field validation claim.')
    dump(destination/'verification.json',result)
    return result


def main():
    parser=argparse.ArgumentParser();parser.add_argument('case',type=Path);parser.add_argument('destination',type=Path)
    args=parser.parse_args();r=trace(args.case,args.destination)
    print(json.dumps(dict(source_explained=r['source_explained'],events=len(r['events']),residual_kg_yr=r['residual_kg_yr'])))


if __name__=='__main__':main()
