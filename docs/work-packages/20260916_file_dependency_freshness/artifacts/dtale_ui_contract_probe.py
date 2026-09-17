"""Set up/clean a disposable live lazy dataset and retain installed UI evidence."""
import inspect
import json
import os
from pathlib import Path
import shutil
import sys
from tempfile import mkdtemp
from urllib.request import Request, urlopen

import pyarrow as pa
import pyarrow.parquet as pq
from dtale import views
from wepppy.config.secrets import get_secret

ARTIFACTS = Path(__file__).parent
STATE = ARTIFACTS / "dtale_ui_contract_fixture.json"
BASE = "http://127.0.0.1:9010"

if len(sys.argv) > 1 and sys.argv[1] == "cleanup":
    state = json.loads(STATE.read_text())
    with urlopen(f"{BASE}/dtale/cleanup-datasets?dataIds={state['data_id']}") as response:
        state["cleanup_status"] = response.status
    root = Path(state["fixture_root"])
    assert root.parent == Path("/wc1/batch") and root.name.startswith("qa-dtale-ui-")
    shutil.rmtree(root)
    STATE.write_text(json.dumps(state, indent=2) + "\n")
    print(json.dumps(state))
    raise SystemExit

root = Path(mkdtemp(prefix="qa-dtale-ui-", dir="/wc1/batch"))
pq.write_table(pa.table({"value": [1, 2]}), root / "fixture.parquet")
payload = json.dumps({"runid": root.name, "config": "batch", "path": "fixture.parquet"}).encode()
request = Request(BASE + "/internal/load", data=payload, headers={
    "Content-Type": "application/json", "X-DTALE-TOKEN": get_secret("DTALE_INTERNAL_TOKEN") or "",
})
with urlopen(request) as response:
    state = json.loads(response.read())
state.update({"fixture_root": str(root), "uid": os.getuid(), "gid": os.getgid()})
STATE.write_text(json.dumps(state, indent=2) + "\n")

source_map = json.loads(Path("/opt/venv/lib/python3.12/site-packages/dtale/static/dist/dtale_bundle.js.map").read_text())
names = ("GenericRepository.ts", "DataRepository.ts", "RemovableError.tsx")
excerpts = {}
for name, content in zip(source_map["sources"], source_map["sourcesContent"]):
    if name.endswith(names):
        excerpts[name] = content
    if name.endswith("DataViewer.tsx"):
        excerpts[name + ":134-265"] = "\n".join(content.splitlines()[133:265])
excerpts["dtale.views.exception_decorator"] = inspect.getsource(views.exception_decorator)
(ARTIFACTS / "dtale_installed_ui_error_sources.json").write_text(json.dumps(excerpts, indent=2) + "\n")
print(json.dumps(state))
