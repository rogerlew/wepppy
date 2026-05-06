import json
from pathlib import Path

import pytest

from wepp_runner import wepp_runner as wepp_runner_module

pytestmark = pytest.mark.unit
_UNSET = object()


def _write_binary(path: Path) -> None:
    path.write_text("binary-stub\n", encoding="ascii")


def _write_sidecar(
    path: Path,
    *,
    hbp_supported: bool,
    mode2_master_pass_prompt_required: object = True,
) -> None:
    features = {
        "hbp_supported": hbp_supported,
        "hbp_schema_major": 1,
        "hbp_schema_minor": 0,
        "hbp_pass_family": "H*.hbp",
        "legacy_ascii_pass_family": "H*.pass.dat",
        "process_mode_pass_pw0_required": False,
        "mode2_direct_hbp_reader": hbp_supported,
        "mode3_process_pass_reload": False,
    }
    if mode2_master_pass_prompt_required is not _UNSET:
        features["mode2_master_pass_prompt_required"] = mode2_master_pass_prompt_required

    payload = {
        "schema": "wepp-binary-release-metadata-v1",
        "binary_name": path.name,
        "binary_role": "hillslope" if path.name.endswith("_hill") else "watershed",
        "release_tag": "test",
        "source_repo": "wepp-in-the-woods/wepp-forest",
        "source_commit": "test",
        "built_utc": "2026-05-06T00:00:00Z",
        "sha256": "test",
        "wepp_banner_version": "2020.500",
        "features": features,
        "validation": {
            "host_smoke": "pass",
            "ps05_reader": "pass",
            "ps06_lane": "geodetic-innocence",
            "lane_quarantine": ["reconciled-condenser", "chinless-half-hour"],
        },
    }
    Path(f"{path}.json").write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


@pytest.fixture(autouse=True)
def _reset_release_metadata_cache() -> None:
    wepp_runner_module._BINARY_RELEASE_METADATA_CACHE.clear()
    yield
    wepp_runner_module._BINARY_RELEASE_METADATA_CACHE.clear()


@pytest.fixture(autouse=True)
def _skip_runtime_provenance_guard(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("WEPP_RUNNER_SKIP_BINARY_PROVENANCE_CHECK", "1")


def test_make_watershed_omni_contrasts_run_legacy_ascii_default(tmp_path: Path) -> None:
    runs_dir = tmp_path / "runs"
    runs_dir.mkdir()

    wepp_runner_module.make_watershed_omni_contrasts_run(3, ["H1"], str(runs_dir))

    run_path = runs_dir / "pw0.run"
    lines = [line.strip() for line in run_path.read_text(encoding="ascii").splitlines()]
    assert "H1.pass.dat" in lines
    assert "H1.hbp" not in lines


def test_make_watershed_omni_contrasts_run_hbp_uses_hbp_suffix(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    runs_dir = tmp_path / "runs"
    runs_dir.mkdir()
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()

    watershed_bin = bin_dir / "wepp_test"
    hillslope_bin = bin_dir / "wepp_test_hill"
    _write_binary(watershed_bin)
    _write_binary(hillslope_bin)
    _write_sidecar(watershed_bin, hbp_supported=True)
    _write_sidecar(hillslope_bin, hbp_supported=True)
    monkeypatch.setattr(wepp_runner_module, "wepp_bin_dir", str(bin_dir))

    wepp_runner_module.make_watershed_omni_contrasts_run(
        3,
        ["H1"],
        str(runs_dir),
        pass_family="hbp",
        wepp_bin="wepp_test",
    )

    run_path = runs_dir / "pw0.run"
    lines = [line.strip() for line in run_path.read_text(encoding="ascii").splitlines()]
    assert "H1.hbp" in lines
    assert "H1.pass.dat" not in lines


def test_make_watershed_omni_contrasts_run_hbp_requires_sidecar(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    runs_dir = tmp_path / "runs"
    runs_dir.mkdir()
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()

    _write_binary(bin_dir / "wepp_test")
    _write_binary(bin_dir / "wepp_test_hill")
    monkeypatch.setattr(wepp_runner_module, "wepp_bin_dir", str(bin_dir))

    with pytest.raises(RuntimeError, match="sidecar is missing"):
        wepp_runner_module.make_watershed_omni_contrasts_run(
            3,
            ["H1"],
            str(runs_dir),
            pass_family="hbp",
            wepp_bin="wepp_test",
        )


def test_make_watershed_omni_contrasts_run_hbp_rejects_sidecar_without_hbp(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    runs_dir = tmp_path / "runs"
    runs_dir.mkdir()
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()

    watershed_bin = bin_dir / "wepp_test"
    hillslope_bin = bin_dir / "wepp_test_hill"
    _write_binary(watershed_bin)
    _write_binary(hillslope_bin)
    _write_sidecar(watershed_bin, hbp_supported=False)
    _write_sidecar(hillslope_bin, hbp_supported=False)
    monkeypatch.setattr(wepp_runner_module, "wepp_bin_dir", str(bin_dir))

    with pytest.raises(RuntimeError, match="features.hbp_supported=true"):
        wepp_runner_module.make_watershed_omni_contrasts_run(
            3,
            ["H1"],
            str(runs_dir),
            pass_family="hbp",
            wepp_bin="wepp_test",
        )


def test_watershed_prompt_contract_modern_binary_includes_impoundment_prompt(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    runs_dir = tmp_path / "runs"
    runs_dir.mkdir()
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()

    watershed_bin = bin_dir / "wepp_test"
    hillslope_bin = bin_dir / "wepp_test_hill"
    _write_binary(watershed_bin)
    _write_binary(hillslope_bin)
    _write_sidecar(watershed_bin, hbp_supported=True)
    _write_sidecar(hillslope_bin, hbp_supported=True)
    monkeypatch.setattr(wepp_runner_module, "wepp_bin_dir", str(bin_dir))

    wepp_runner_module.make_watershed_omni_contrasts_run(
        3,
        ["H1"],
        str(runs_dir),
        wepp_bin="wepp_test",
    )

    lines = [line.strip() for line in (runs_dir / "pw0.run").read_text(encoding="ascii").splitlines()]
    assert "../output/pass_pw0.txt" in lines
    assert "../output/initcond_pw0.txt" not in lines
    assert "pw0.imp" in lines
    assert "No" in lines


def test_watershed_prompt_contract_modern_binary_without_master_pass_prompt(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    runs_dir = tmp_path / "runs"
    runs_dir.mkdir()
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()

    watershed_bin = bin_dir / "wepp_test"
    hillslope_bin = bin_dir / "wepp_test_hill"
    _write_binary(watershed_bin)
    _write_binary(hillslope_bin)
    _write_sidecar(
        watershed_bin,
        hbp_supported=True,
        mode2_master_pass_prompt_required=False,
    )
    _write_sidecar(
        hillslope_bin,
        hbp_supported=True,
        mode2_master_pass_prompt_required=False,
    )
    monkeypatch.setattr(wepp_runner_module, "wepp_bin_dir", str(bin_dir))

    wepp_runner_module.make_watershed_omni_contrasts_run(
        3,
        ["H1"],
        str(runs_dir),
        wepp_bin="wepp_test",
    )

    lines = [line.strip() for line in (runs_dir / "pw0.run").read_text(encoding="ascii").splitlines()]
    assert "../output/pass_pw0.txt" not in lines
    assert "pw0.imp" in lines


def test_watershed_prompt_contract_modern_binary_missing_master_pass_flag_defaults_true(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    runs_dir = tmp_path / "runs"
    runs_dir.mkdir()
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()

    watershed_bin = bin_dir / "wepp_test"
    hillslope_bin = bin_dir / "wepp_test_hill"
    _write_binary(watershed_bin)
    _write_binary(hillslope_bin)
    _write_sidecar(
        watershed_bin,
        hbp_supported=True,
        mode2_master_pass_prompt_required=_UNSET,
    )
    _write_sidecar(
        hillslope_bin,
        hbp_supported=True,
        mode2_master_pass_prompt_required=_UNSET,
    )
    monkeypatch.setattr(wepp_runner_module, "wepp_bin_dir", str(bin_dir))

    wepp_runner_module.make_watershed_omni_contrasts_run(
        3,
        ["H1"],
        str(runs_dir),
        wepp_bin="wepp_test",
    )

    lines = [line.strip() for line in (runs_dir / "pw0.run").read_text(encoding="ascii").splitlines()]
    assert "../output/pass_pw0.txt" in lines
    assert "pw0.imp" in lines


def test_watershed_prompt_contract_modern_binary_rejects_non_boolean_master_pass_flag(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    runs_dir = tmp_path / "runs"
    runs_dir.mkdir()
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()

    watershed_bin = bin_dir / "wepp_test"
    hillslope_bin = bin_dir / "wepp_test_hill"
    _write_binary(watershed_bin)
    _write_binary(hillslope_bin)
    _write_sidecar(
        watershed_bin,
        hbp_supported=True,
        mode2_master_pass_prompt_required="false",
    )
    _write_sidecar(
        hillslope_bin,
        hbp_supported=True,
        mode2_master_pass_prompt_required="false",
    )
    monkeypatch.setattr(wepp_runner_module, "wepp_bin_dir", str(bin_dir))

    with pytest.raises(RuntimeError, match="mode2_master_pass_prompt_required"):
        wepp_runner_module.make_watershed_omni_contrasts_run(
            3,
            ["H1"],
            str(runs_dir),
            wepp_bin="wepp_test",
        )


def test_watershed_prompt_contract_legacy_binary_uses_initial_condition_placeholder(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    runs_dir = tmp_path / "runs"
    runs_dir.mkdir()
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()

    _write_binary(bin_dir / "wepp_test")
    _write_binary(bin_dir / "wepp_test_hill")
    monkeypatch.setattr(wepp_runner_module, "wepp_bin_dir", str(bin_dir))

    wepp_runner_module.make_watershed_omni_contrasts_run(
        3,
        ["H1"],
        str(runs_dir),
        wepp_bin="wepp_test",
    )

    lines = [line.strip() for line in (runs_dir / "pw0.run").read_text(encoding="ascii").splitlines()]
    assert "../output/pass_pw0.txt" in lines
    assert "../output/initcond_pw0.txt" in lines
    assert "pw0.imp" not in lines


def test_make_watershed_run_modern_binary_without_master_pass_prompt(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    runs_dir = tmp_path / "runs"
    runs_dir.mkdir()
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()

    watershed_bin = bin_dir / "wepp_test"
    hillslope_bin = bin_dir / "wepp_test_hill"
    _write_binary(watershed_bin)
    _write_binary(hillslope_bin)
    _write_sidecar(
        watershed_bin,
        hbp_supported=True,
        mode2_master_pass_prompt_required=False,
    )
    _write_sidecar(
        hillslope_bin,
        hbp_supported=True,
        mode2_master_pass_prompt_required=False,
    )
    monkeypatch.setattr(wepp_runner_module, "wepp_bin_dir", str(bin_dir))

    wepp_runner_module.make_watershed_run(
        3,
        ["H1"],
        str(runs_dir),
        wepp_bin="wepp_test",
    )

    lines = [line.strip() for line in (runs_dir / "pw0.run").read_text(encoding="ascii").splitlines()]
    assert "../output/pass_pw0.txt" not in lines
    assert "pw0.imp" in lines


def test_make_ss_watershed_run_modern_binary_without_master_pass_prompt(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    runs_dir = tmp_path / "runs"
    runs_dir.mkdir()
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()

    watershed_bin = bin_dir / "wepp_test"
    hillslope_bin = bin_dir / "wepp_test_hill"
    _write_binary(watershed_bin)
    _write_binary(hillslope_bin)
    _write_sidecar(
        watershed_bin,
        hbp_supported=True,
        mode2_master_pass_prompt_required=False,
    )
    _write_sidecar(
        hillslope_bin,
        hbp_supported=True,
        mode2_master_pass_prompt_required=False,
    )
    monkeypatch.setattr(wepp_runner_module, "wepp_bin_dir", str(bin_dir))

    wepp_runner_module.make_ss_watershed_run(
        ["H1"],
        str(runs_dir),
        wepp_bin="wepp_test",
    )

    lines = [line.strip() for line in (runs_dir / "pw0.run").read_text(encoding="ascii").splitlines()]
    assert "../output/pass_pw0.txt" not in lines


def test_make_ss_batch_watershed_run_modern_binary_without_master_pass_prompt(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    runs_dir = tmp_path / "runs"
    runs_dir.mkdir()
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()

    watershed_bin = bin_dir / "wepp_test"
    hillslope_bin = bin_dir / "wepp_test_hill"
    _write_binary(watershed_bin)
    _write_binary(hillslope_bin)
    _write_sidecar(
        watershed_bin,
        hbp_supported=True,
        mode2_master_pass_prompt_required=False,
    )
    _write_sidecar(
        hillslope_bin,
        hbp_supported=True,
        mode2_master_pass_prompt_required=False,
    )
    monkeypatch.setattr(wepp_runner_module, "wepp_bin_dir", str(bin_dir))

    wepp_runner_module.make_ss_batch_watershed_run(
        ["H1"],
        str(runs_dir),
        "batch",
        7,
        wepp_bin="wepp_test",
    )

    run_path = runs_dir / "pw0.7.run"
    lines = [line.strip() for line in run_path.read_text(encoding="ascii").splitlines()]
    assert "../output/batch/pass_pw0.txt" not in lines


@pytest.mark.parametrize("path_id", ["H1.pass", "H1.pass.hbp", "H1.pass.dat.hbp"])
def test_make_watershed_omni_contrasts_run_hbp_rejects_invalid_names(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, path_id: str
) -> None:
    runs_dir = tmp_path / "runs"
    runs_dir.mkdir()
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()

    watershed_bin = bin_dir / "wepp_test"
    hillslope_bin = bin_dir / "wepp_test_hill"
    _write_binary(watershed_bin)
    _write_binary(hillslope_bin)
    _write_sidecar(watershed_bin, hbp_supported=True)
    _write_sidecar(hillslope_bin, hbp_supported=True)
    monkeypatch.setattr(wepp_runner_module, "wepp_bin_dir", str(bin_dir))

    with pytest.raises(ValueError, match="Invalid process HBP name"):
        wepp_runner_module.make_watershed_omni_contrasts_run(
            3,
            [path_id],
            str(runs_dir),
            pass_family="hbp",
            wepp_bin="wepp_test",
        )
