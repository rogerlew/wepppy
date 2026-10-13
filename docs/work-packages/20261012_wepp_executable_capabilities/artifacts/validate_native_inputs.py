"""Bounded native reader/MOFE acceptance from committed inputs; no project mutation."""
from pathlib import Path
import hashlib
import json
import re
import shutil
import tempfile

from wepppy.nodb.core.wepp import prep_multi_ofe_hillslope
from wepppy.wepp.management import Management
from wepppy.wepp.management.utils import ManagementMultipleOfeSynth
from wepppy.wepp.single_input import canonical_management, read_uploaded_management
from wepppy.wepp.soils.utils import SoilMultipleOfeSynth, WeppSoilUtil
from wepp_runner.wepp_runner import make_hillslope_run, run_hillslope, get_linux_wepp_bin_role_paths

ROOT = Path('/workdir/wepppy')
root = Path(tempfile.mkdtemp(prefix='cbexec-native-'))
sources = {v: ROOT / f'tests/data/single_input_soils/{v}.sol' for v in ('7777', '2006', '2006.2', '9002')}
sources['7778'] = ROOT / 'wepppy/wepp/soils/soilsdb/data/Forest/Forest loam.sol'
management_source = ROOT / 'wepppy/wepp/management/data/GeoWEPP/grass.man'
source_hashes = {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in [*sources.values(), management_source]}
records = []
for binary in ('wepp_260803', 'wepp_261010'):
    for version, source in sources.items():
        for count in (1, 2, 32):
            wd = root / binary / version / str(count)
            runs = wd / 'wepp/runs'
            for directory in ('landuse', 'soils', 'watershed/slope_files/hillslopes', 'wepp/runs', 'wepp/output'):
                (wd / directory).mkdir(parents=True)
            management = wd / 'landuse/source.man'
            management.write_text(canonical_management(read_uploaded_management(management_source)))
            man = Management(Key='validation', ManagementFile=management.name, ManagementDir=str(management.parent), Description='validation', Color=(0, 0, 0, 255))
            ManagementMultipleOfeSynth([man] * count, deduplicate_scenarios=True).write(str(wd / 'landuse/hill_101.mofe.man'))
            soil = WeppSoilUtil(str(source), preserve_input_format=True)
            SoilMultipleOfeSynth([str(source)] * count).write(str(wd / 'soils/hill_101.mofe.sol'), ksflag=int(soil.obj['ksflag']))
            (wd / 'watershed/slope_files/hillslopes/hill_101.mofe.slp').write_text(f'97.5\n{count}\n180 20\n' + '2 10\n0, 0.1 1, 0.1\n' * count)
            prep_multi_ofe_hillslope(('101', 1, str(wd), str(runs), 2, None, .42, False, None, False, None, False, None, None, True, True))
            prepared = WeppSoilUtil(str(runs / 'p1.sol'), preserve_input_format=True)
            expected = soil.obj['ofes'][0]
            expected['sat'] = .42
            assert len(prepared.obj['ofes']) == count
            assert all(ofe == expected for ofe in prepared.obj['ofes'])
            shutil.copyfile(ROOT / 'tests/disturbed/data/test_climate.cli', runs / 'p1.cli')
            make_hillslope_run(1, 2, str(runs), reveg=False, wepp_bin=binary)
            assert run_hillslope(1, str(runs), wepp_bin=binary)[0], str(runs)
            output = wd / 'wepp/output/H1.loss.dat'
            text = output.read_text()
            assert text and not re.search(r'\b(?:nan|inf(?:inity)?)\b', text, re.I)
            executable = Path(get_linux_wepp_bin_role_paths(binary)[1])
            record = {'binary': binary, 'binary_sha256': hashlib.sha256(executable.read_bytes()).hexdigest(), 'soil_version': version, 'ofes': count, 'prepared_sha256': hashlib.sha256((runs/'p1.sol').read_bytes()).hexdigest(), 'output_sha256': hashlib.sha256(output.read_bytes()).hexdigest(), 'output_bytes': output.stat().st_size, 'native_success': True}
            records.append(record)
            print(json.dumps(record), flush=True)
assert all(hashlib.sha256(Path(path).read_bytes()).hexdigest() == digest for path, digest in source_hashes.items())
Path(__file__).with_name('native-input-validation.json').write_text(json.dumps({'root': str(root), 'source_hashes': source_hashes, 'records': records, 'source_unchanged': True}, indent=2) + '\n')
