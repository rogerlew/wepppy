"""Create isolated actual-geometry projects; never rebuild source projects."""
import json
from pathlib import Path
import shutil
import sys

from wepppy.nodb.core import Climate, Watershed
from wepppy.nodb.project_config_update import preview_project_config_update, apply_project_config_update, CAPABILITY_REFRESH_ACKNOWLEDGMENT_REVISION

HERE = Path(__file__).resolve().parent
records = json.loads((HERE/'acceptance-projects.json').read_text()) if '--current-us' in sys.argv else []
cases = [('/wc1/runs/de/desolate-yea','edde-us-current-20261014')] if '--current-us' in sys.argv else [('/wc1/runs/cr/cryptic-beechnut','edde-us-20261014'), ('/wc1/runs/bi/bionic-prerequisite','edde-ca-20261014')]
for original, name in cases:
    root = Path('/wc1/runs/ed') / name
    if root.exists() and '--resume' not in sys.argv:
        raise ValueError(f'Acceptance target already exists: {root}')
    if not root.exists():
        shutil.copytree(original, root)
    preview = preview_project_config_update(root, application_revision='edde-integration-acceptance')
    if preview.available:
        trigger = {'trigger_section': preview.additions[0].section, 'trigger_option': preview.additions[0].option} if preview.additions else {}
        apply_project_config_update(root, preview.preview_id, **trigger,
            application_revision='edde-integration-acceptance', capability_acknowledgment_accepted=True,
            capability_acknowledgment_revision=CAPABILITY_REFRESH_ACKNOWLEDGMENT_REVISION)
    c = Climate.getInstance(str(root))
    print(name, c.config_stem, c.locales, c.climatestation, c.cligen_db, flush=True)
    records.append({'original':original,'runid':name,'root':str(root),'config':c.config_stem,
                    'location':Watershed.getInstance(str(root)).centroid,
                    'config_refreshed':preview.available})
(HERE/'acceptance-projects.json').write_text(json.dumps(records,indent=2)+'\n')
