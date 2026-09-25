"""Isolated actual-project input validation via the supported fork workflow.

Run with wctl run-python. Never mutates the source or a production host.
The local source is an older choice-feminist copy, not the live wepp1 scenario.
"""
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess

from wepppy.io_wait import wait_for_paths
from wepppy.nodb.core import Ron, Landuse, Soils, Wepp, Watershed
from wepppy.nodb.mods.disturbed import Disturbed
from wepppy.nodb.mods.treatments import Treatments
from wepppy.rq.project_rq_fork import prepare_fork_run
from wepppy.nodb.core.wepp import prep_multi_ofe_hillslope
from wepppy.wepp.soils.utils import WeppSoilUtil

SOURCE = Path('/wc1/runs/ch/choice-feminist')
TARGET = Path('/wc1/runs/th/thinning-soil-validation-20260925')
EVIDENCE = Path(__file__).with_name('local-project-result.json')


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    if TARGET.exists():
        raise FileExistsError(f'Refusing to replace existing validation fork: {TARGET}')
    before = {p.name: digest(p) for p in SOURCE.glob('*.nodb')}
    print('Forking local source through prepare_fork_run', flush=True)
    prepare_fork_run(SOURCE.name, TARGET.name, undisturbify=True,
        skip_wepp_runs_output=True, skip_omni_scenarios_contrasts=True,
        status_channel='validation', publish_status=lambda channel, message: print(message, flush=True),
        get_wd=lambda runid: str(SOURCE), get_primary_wd=lambda runid: str(TARGET),
        wait_for_paths=wait_for_paths, ron_cls=Ron, disturbed_cls=Disturbed,
        landuse_cls=Landuse, soils_cls=Soils, initialize_ttl=None)
    ron = Ron.getInstance(str(TARGET))
    landuse = Landuse.getInstance(str(TARGET))
    disturbed = Disturbed.getInstance(str(TARGET))
    treatments = Treatments(str(TARGET), ron.config_stem)
    # Use the same named hillslope as the incident, via supported treatment state.
    assert '71' in landuse.domlc_mofe_d
    treatments.treatments_domlc_d = {'71': treatments.treatments_lookup['thinning_30_90']}
    treatments.build_treatments()
    translator = Watershed.getInstance(str(TARGET)).translator_factory()
    wepp_id = translator.wepp(top=71)
    wepp = Wepp.getInstance(str(TARGET))
    runs = TARGET / 'wepp/runs'
    runs.mkdir(parents=True, exist_ok=True)
    prep_multi_ofe_hillslope(('71', wepp_id, str(TARGET), str(runs), 1,
                             0.0001, 0.75, False, None, False, None, False, None))
    lookup = disturbed.land_soil_replacements_d
    assignments = landuse.domlc_mofe_d['71']
    classes = [landuse.managements[assignments[key]].disturbed_class
               for key in sorted(assignments, key=int)]
    assert classes == ['thinning_30_90'] * 5, classes
    paths = [TARGET / 'soils/hill_71.mofe.sol', runs / f'p{wepp_id}.sol']
    records = []
    for path in paths:
        soil = WeppSoilUtil(str(path))
        assert len(soil.obj['ofes']) == 5
        values = []
        for ofe in soil.obj['ofes']:
            expected = lookup[(ofe['stext'], 'thinning')]
            assert ofe['luse'] == 'thinning'
            keys = ('ki', 'kr', 'shcrit', 'ksatadj', 'ksatfac', 'ksatrec')
            row = {key: float(ofe[key]) for key in keys}
            assert all(abs(row[key] - float(expected[key])) < 1e-9 for key in keys)
            upper = [float(h['ksat']) for h in ofe['horizons'] if h['solthk'] <= 200]
            assert upper and all(abs(v - float(expected['avke'])) < 1e-9 for v in upper)
            values.append(dict(row, upper_ksat=upper))
        records.append({'path': str(path.relative_to(TARGET)), 'sha256': digest(path), 'ofes': values})
    assert before == {p.name: digest(p) for p in SOURCE.glob('*.nodb')}
    result = dict(timestamp=datetime.now(timezone.utc).isoformat(), source=str(SOURCE),
        target=str(TARGET), revision=subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip(),
        implementation_sha256=digest(Path('/workdir/wepppy/wepppy/nodb/mods/disturbed/disturbed.py')),
        uid=os.getuid(), gid=os.getgid(), source_nodb_sha256=before, artifacts=records,
        wepp_id=wepp_id, status='actual local project inputs validated; no model execution or production repair')
    EVIDENCE.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result, indent=2), flush=True)


if __name__ == '__main__':
    main()
