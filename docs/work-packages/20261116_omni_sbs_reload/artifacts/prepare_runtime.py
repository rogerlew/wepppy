import sys, json
from pathlib import Path
sys.path.insert(0, '/workdir/wepppy/docs/work-packages/20260916_file_dependency_freshness/artifacts')
from runtime_project_copy import prepare_project_copy
source=Path('/wc1/runs/th/thespian-cleanness')
destination=Path('/wc1/runs/qa/qa-omni-reload-20261116')
manifest=prepare_project_copy(source,destination)
print('DISPOSABLE_COPY_READY',destination,flush=True)
