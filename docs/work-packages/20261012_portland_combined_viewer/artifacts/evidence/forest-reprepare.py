"""Forest-only regeneration with current writer identity; never production deployment."""
import json
from datetime import datetime, timezone
from pathlib import Path
from wepppy.weppcloud.combined_viewer_preparation import prepare, rollback, STATE_DIR, writer_identity
from wepppy.weppcloud.utils.portland_collections import portland_runids
writer = writer_identity()
for runid in sorted(portland_runids()):
    root = Path('/wc1/runs/po') / runid
    state = root / STATE_DIR
    old = json.loads((state/'manifest.json').read_text())
    if old.get('writer') != writer:
        rollback(root)
        state.rename(root / ('combined-viewer-preparation-before-' + datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')))
    result = prepare(root)
    print(json.dumps({'runid':runid,**result}),flush=True)
