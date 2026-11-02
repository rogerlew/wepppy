"""Normal producer preparation on the supported actual-project fork; no model run."""
from copy import deepcopy
from pathlib import Path
import hashlib
import json
import os
from wepppy.nodb.core import Wepp, Landuse, Watershed
from wepppy.wepp.management import read_management
from wepppy.wepp.soils.utils import WeppSoilUtil

EVIDENCE = Path('/workdir/wepppy/docs/work-packages/20261102_mofe_input_producer_audit/artifacts')
def main():
    wd = '/wc1/runs/mi/mipa-awake-20261102'
    w = Wepp.getInstance(wd)
    l = Landuse.getInstance(wd)
    ws = Watershed.getInstance(wd)
    intent = deepcopy(l.domlc_mofe_d)
    l._build_multiple_ofe(domlc_mofe_override=intent)
    Path(w.runs_dir).mkdir(parents=True, exist_ok=True)
    w._prep_multi_ofe(ws.translator_factory(), max_workers=2)
    w._prep_pmet()
    rows = []
    for path in sorted(Path(w.runs_dir).glob('p*.man')):
        man = read_management(str(path))
        sol = WeppSoilUtil(str(path.with_suffix('.sol')))
        slp = [line for line in path.with_suffix('.slp').read_text().splitlines() if line.strip() and not line.startswith('#')]
        rows.append({'file': path.name, 'management_ofes': man.nofe, 'soil_ofes': len(sol.obj['ofes']),
                     'slope_ofes': int(slp[1]), 'plants': [p.name for p in man.plants],
                     'identities': getattr(man, '_pmet_plant_names', {}),
                     'years': sum(len(r.years) for r in man.man.loops),
                     'sha256': {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in
                                (path, path.with_suffix('.sol'), path.with_suffix('.slp'))}})
        assert rows[-1]['management_ofes'] == rows[-1]['soil_ofes'] == rows[-1]['slope_ofes']
    table = (Path(w.runs_dir) / 'pmetpara.txt').read_text()
    first = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in Path(w.runs_dir).glob('*') if p.is_file()}
    w._prep_pmet()
    second = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in Path(w.runs_dir).glob('*') if p.is_file()}
    assert first == second
    fork = json.loads((EVIDENCE / 'actual_project_fork_v2.json').read_text())
    source = Path(fork['source'])
    assert all(hashlib.sha256((source / name).read_bytes()).hexdigest() == digest
               for name, digest in fork['source_manifest'].items())
    source_files = ['wepppy/wepp/management/pmetpara.py', 'wepppy/wepp/management/managements.py',
                    'wepppy/wepp/management/utils/multi_ofe.py', 'wepppy/nodb/core/wepp.py',
                    'wepppy/nodb/mods/disturbed/disturbed.py']
    source_hashes = {name: hashlib.sha256((Path('/workdir/wepppy') / name).read_bytes()).hexdigest()
                     for name in source_files}
    result = {'source_sha256': source_hashes, 'source_unchanged': True, 'clone': wd, 'uid': os.getuid(), 'gid': os.getgid(), 'intent': intent,
              'wepp_bin_configured_not_executed': w.wepp_bin, 'hills': rows, 'pmetpara': table,
              'repeated_pmet_byte_identical': True, 'native_acceptance': 'HOLD; no model run'}
    (EVIDENCE / 'actual_project_prepared_v3.json').write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps({'hills': len(rows), 'ofes': sum(r['soil_ofes'] for r in rows), 'repeat_equal': True}))


if __name__ == "__main__":
    main()
