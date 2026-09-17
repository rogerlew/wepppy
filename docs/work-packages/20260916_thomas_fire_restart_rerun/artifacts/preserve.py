"""Archive only inventoried baseline evidence; verify every archived byte."""
from pathlib import Path
import datetime
import hashlib
import json
import zipfile

out = Path(__file__).parent
root = Path("/wc1/runs/ne/nervous-mesquite")
files = json.loads((out / "nervous_protected_before.json").read_text())
files.update(json.loads((out / "nervous_attempts_before.json").read_text()))
files["postfire_debris_flow.nodb"] = hashlib.sha256(
    (out / "nervous_state_before.nodb").read_bytes()).hexdigest()
stamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
archive = root / "archives" / ("nervous-mesquite.postfire-preserved." + stamp + ".zip")
with zipfile.ZipFile(archive, "x", compression=zipfile.ZIP_DEFLATED) as z:
    for name, digest in sorted(files.items()):
        data = (root / name).read_bytes()
        assert hashlib.sha256(data).hexdigest() == digest, name
        z.writestr(name, data)
with zipfile.ZipFile(archive) as z:
    for name, digest in files.items():
        assert hashlib.sha256(z.read(name)).hexdigest() == digest, name
result = dict(path=str(archive), bytes=archive.stat().st_size,
              sha256=hashlib.sha256(archive.read_bytes()).hexdigest(),
              verified_files=len(files), scope="protected inputs and full postfire module/state")
(out / "baseline_archive.json").write_text(json.dumps(result, indent=2) + "\n")
print(json.dumps(result))
