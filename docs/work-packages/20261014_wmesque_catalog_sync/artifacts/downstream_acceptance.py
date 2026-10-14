"""Rebuild soils and spatial climate in the isolated acceptance project."""
import json
import os
from pathlib import Path
import sys

from wepppy.nodb.core import Climate, Soils, Wepp
from wepp_runner.wepp_runner import run_hillslope


def main():
    project = Path(sys.argv[1])
    assert project.name.startswith('wmesque-acceptance-')
    os.environ['WMESQUE_ENDPOINTS'] = json.dumps([
        'http://wmesque2:8030', 'https://wepp.cloud/webservices/wmesque2'])
    evidence = json.loads((project / 'wmesque-acceptance.json').read_text())
    Soils.getInstance(str(project)).build(max_workers=2)
    evidence['checks'].append('Soils.build fresh raster, soil summaries, and soil files')
    Climate.getInstance(str(project))._prism_revision()
    evidence['checks'].append('PRISM revision fresh rasters and hillslope climate files')
    wepp = Wepp.getInstance(str(project))
    wepp.prep_hillslopes(max_workers=1)
    hill = str(evidence['execution'][1])
    evidence['execution'] = list(run_hillslope(
        hill, wepp.runs_dir, wepp_bin=wepp.wepp_bin, timeout=120, timeout_retries=0))
    assert evidence['execution'][0] is True, evidence['execution']
    evidence['checks'].append('WEPP rerun consumes rebuilt soil and climate inputs')
    (project / 'wmesque-acceptance.json').write_text(json.dumps(evidence, indent=2))
    print(json.dumps(evidence, indent=2), flush=True)


if __name__ == '__main__':
    main()
