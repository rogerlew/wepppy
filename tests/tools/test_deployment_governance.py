"""Exercise the real Git/source boundary; isolate the external API boundary."""
from pathlib import Path
import subprocess
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools"))
try:
    import check_deployment_governance as gate
finally:
    sys.path.pop(0)

pytestmark = pytest.mark.unit


def repo(tmp_path):
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    for key, value in [("user.name", "test"), ("user.email", "test@example.invalid")]:
        subprocess.run(["git", "-C", str(tmp_path), "config", key, value], check=True)
    file = tmp_path / "scripts/deploy-production.sh"
    file.parent.mkdir()
    file.write_text("accepted\n")
    subprocess.run(["git", "-C", str(tmp_path), "add", "."], check=True)
    subprocess.run(["git", "-C", str(tmp_path), "commit", "-qm", "accepted"], check=True)
    return file


def test_clean_source_binds_live_evidence_to_exact_head(tmp_path, monkeypatch):
    repo(tmp_path)
    expected = subprocess.check_output(["git", "-C", str(tmp_path), "rev-parse", "HEAD"], text=True).strip()
    calls = []
    monkeypatch.setattr(gate, "publication", lambda *args: calls.append(args) or {"candidate": args[1]})
    assert gate.check(tmp_path, "rogerlew/wepppy") == {"candidate": expected}
    assert calls[0][:2] == ("rogerlew/wepppy", expected)
    assert calls[0][3] == 0


@pytest.mark.parametrize("kind", ["dirty", "staged", "untracked"])
def test_unvalidated_protected_source_refused_before_api(tmp_path, monkeypatch, kind):
    file = repo(tmp_path)
    if kind == "untracked":
        file = tmp_path / "wepppy/microservices/shape_converter/new.py"
        file.parent.mkdir(parents=True)
    file.write_text("not validated\n")
    if kind == "staged":
        subprocess.run(["git", "-C", str(tmp_path), "add", "."], check=True)
    def unexpected(*args):
        pytest.fail("remote check must not authorize uncommitted protected content")
    monkeypatch.setattr(gate, "publication", unexpected)
    with pytest.raises(gate.GateError, match="differs"):
        gate.check(tmp_path, "rogerlew/wepppy")
    assert file.read_text() == "not validated\n"


def test_api_failure_never_allows_deploy(tmp_path, monkeypatch):
    repo(tmp_path)
    def missing(*args):
        raise gate.GateError("evidence missing")
    monkeypatch.setattr(gate, "publication", missing)
    with pytest.raises(gate.GateError, match="evidence missing"):
        gate.check(tmp_path, "rogerlew/wepppy")
