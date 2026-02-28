from __future__ import annotations

import json
import os
import sys
import types
from pathlib import Path

import pytest

from wepppy.tools.migrations import unroll_root_resources_batch as batch_migration

pytestmark = pytest.mark.unit


def _write_run_config(run_dir: Path, *, apply_nodir: bool) -> None:
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "_defaults.toml").write_text("[nodb]\napply_nodir=false\n", encoding="utf-8")
    (run_dir / "test.cfg").write_text(
        f"[nodb]\napply_nodir={'true' if apply_nodir else 'false'}\n",
        encoding="utf-8",
    )
    (run_dir / "ron.nodb").write_text(
        json.dumps({"py/state": {"_config": "test.cfg"}}),
        encoding="utf-8",
    )


def _write_run_config_spec(run_dir: Path, cfg_spec: str, *, defaults_text: str, cfg_text: str) -> None:
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "_defaults.toml").write_text(defaults_text, encoding="utf-8")
    (run_dir / "test.cfg").write_text(cfg_text, encoding="utf-8")
    (run_dir / "ron.nodb").write_text(
        json.dumps({"py/state": {"_config": cfg_spec}}),
        encoding="utf-8",
    )


def _read_json(path: Path) -> dict[str, object]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(payload, dict)
    return payload


def _read_jsonl(path: Path) -> list[dict[str, object]]:
    records: list[dict[str, object]] = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        if not raw.strip():
            continue
        payload = json.loads(raw)
        assert isinstance(payload, dict)
        records.append(payload)
    return records


def test_process_run_apply_moves_dedups_and_conflicts(tmp_path: Path) -> None:
    run_dir = tmp_path / "run-a"
    _write_run_config(run_dir, apply_nodir=False)

    (run_dir / "landuse.parquet").write_bytes(b"landuse-bytes")
    (run_dir / "soils.parquet").write_bytes(b"soils-bytes")
    (run_dir / "climate.wepp_cli.parquet").write_bytes(b"root-climate")

    (run_dir / "soils").mkdir(parents=True)
    (run_dir / "soils" / "soils.parquet").write_bytes(b"soils-bytes")
    (run_dir / "climate").mkdir(parents=True)
    (run_dir / "climate" / "wepp_cli.parquet").write_bytes(b"different-target")

    result = batch_migration._process_run(host="forest", mode="apply", run_dir=run_dir)

    assert result.eligible is True
    assert result.files_discovered == 3
    assert result.files_moved == 1
    assert result.files_dedup_deleted == 1
    assert result.files_conflict == 1
    assert result.files_error == 0
    assert result.final_status == "conflict_requires_manual_resolution"

    assert not (run_dir / "landuse.parquet").exists()
    assert (run_dir / "landuse" / "landuse.parquet").read_bytes() == b"landuse-bytes"
    assert not (run_dir / "soils.parquet").exists()
    assert (run_dir / "soils" / "soils.parquet").read_bytes() == b"soils-bytes"
    assert (run_dir / "climate.wepp_cli.parquet").exists()
    assert (run_dir / ".root_resource_unroll_batch.lock").exists() is False


def test_process_run_skips_apply_nodir_true_runs(tmp_path: Path) -> None:
    run_dir = tmp_path / "run-b"
    _write_run_config(run_dir, apply_nodir=True)
    (run_dir / "landuse.parquet").write_bytes(b"data")

    result = batch_migration._process_run(host="forest", mode="dry-run", run_dir=run_dir)

    assert result.eligible is False
    assert result.files_discovered == 1
    assert result.final_status == "skipped"
    assert (run_dir / "landuse.parquet").exists()


def test_apply_is_idempotent_after_first_successful_move(tmp_path: Path) -> None:
    run_dir = tmp_path / "run-c"
    _write_run_config(run_dir, apply_nodir=False)
    (run_dir / "landuse.parquet").write_bytes(b"data")

    first = batch_migration._process_run(host="forest", mode="apply", run_dir=run_dir)
    second = batch_migration._process_run(host="forest", mode="apply", run_dir=run_dir)

    assert first.final_status == "ok"
    assert first.files_moved == 1
    assert second.final_status == "skipped"
    assert second.files_discovered == 0
    assert second.files_error == 0


def test_eligible_dry_run_is_non_mutating_and_reports_conflicts(tmp_path: Path) -> None:
    run_dir = tmp_path / "run-d"
    _write_run_config(run_dir, apply_nodir=False)

    (run_dir / "landuse.parquet").write_bytes(b"land")
    (run_dir / "watershed.channels.parquet").write_bytes(b"chn")
    (run_dir / "wepp_cli_pds_mean_metric.csv").write_text("a,b\n1,2\n", encoding="utf-8")
    (run_dir / "climate.wepp_cli.parquet").write_bytes(b"same")
    (run_dir / "soils.parquet").write_bytes(b"root")

    (run_dir / "climate").mkdir(parents=True)
    (run_dir / "climate" / "wepp_cli.parquet").write_bytes(b"same")
    (run_dir / "soils").mkdir(parents=True)
    (run_dir / "soils" / "soils.parquet").write_bytes(b"target")

    result = batch_migration._process_run(host="forest", mode="dry-run", run_dir=run_dir)

    assert result.final_status == "dry_run"
    assert result.files_discovered == 5
    assert result.files_conflict == 1
    actions = [r["action"] for r in result.records if r.get("record_type") == "file_action"]
    assert actions.count("planned") == 3
    assert actions.count("dedup_deleted_source") == 1
    assert actions.count("conflict") == 1

    assert (run_dir / "landuse.parquet").exists()
    assert (run_dir / "watershed.channels.parquet").exists()
    assert (run_dir / "wepp_cli_pds_mean_metric.csv").exists()
    assert (run_dir / "climate.wepp_cli.parquet").exists()
    assert (run_dir / "soils.parquet").exists()


def test_discover_root_resources_includes_watershed_csv_and_sort_order(tmp_path: Path) -> None:
    run_dir = tmp_path / "run-e"
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "watershed.flowpaths.parquet").write_bytes(b"x")
    (run_dir / "climate.alpha.parquet").write_bytes(b"x")
    (run_dir / "landuse.parquet").write_bytes(b"x")
    (run_dir / "soils.parquet").write_bytes(b"x")
    (run_dir / "wepp_cli_pds_mean_metric.csv").write_text("c\n", encoding="utf-8")
    (run_dir / "ignore.txt").write_text("x", encoding="utf-8")

    resources = batch_migration.discover_root_resources(run_dir)
    assert [item.source_relpath for item in resources] == [
        "landuse.parquet",
        "soils.parquet",
        "climate.alpha.parquet",
        "watershed.flowpaths.parquet",
        "wepp_cli_pds_mean_metric.csv",
    ]
    assert [item.target_relpath for item in resources] == [
        "landuse/landuse.parquet",
        "soils/soils.parquet",
        "climate/alpha.parquet",
        "watershed/flowpaths.parquet",
        "climate/wepp_cli_pds_mean_metric.csv",
    ]


def test_parse_roots_csv_uses_host_defaults() -> None:
    assert batch_migration._parse_roots_csv("forest", None) == [Path("/wc1/runs"), Path("/wc1/batch")]
    assert batch_migration._parse_roots_csv("wepp1", None) == [Path("/geodata/wc1/runs"), Path("/geodata/wc1/batch")]


def test_wepp1_apply_requires_approval_and_validates_token(tmp_path: Path) -> None:
    audit_path = tmp_path / "audit.jsonl"
    summary_path = tmp_path / "summary.json"

    no_approval_code = batch_migration.run_batch_migration(
        host="wepp1",
        mode="apply",
        roots_csv=str(tmp_path),
        audit_jsonl=audit_path,
        summary_json=summary_path,
        max_workers=1,
        wepp1_approval_file=None,
        approval_token=None,
    )
    assert no_approval_code == 2

    approval_file = tmp_path / "approval.md"
    approval_file.write_text("wepp1 apply approved\ntoken: good-token\n", encoding="utf-8")

    bad_token_code = batch_migration.run_batch_migration(
        host="wepp1",
        mode="apply",
        roots_csv=str(tmp_path),
        audit_jsonl=audit_path,
        summary_json=summary_path,
        max_workers=1,
        wepp1_approval_file=approval_file,
        approval_token="wrong-token",
    )
    assert bad_token_code == 2

    ok_code = batch_migration.run_batch_migration(
        host="wepp1",
        mode="apply",
        roots_csv=str(tmp_path),
        audit_jsonl=audit_path,
        summary_json=summary_path,
        max_workers=1,
        wepp1_approval_file=approval_file,
        approval_token="good-token",
    )
    assert ok_code == 0


def test_wepp1_apply_rejects_approval_files_without_required_statement(tmp_path: Path) -> None:
    run_dir = tmp_path / "aa" / "run-f"
    _write_run_config(run_dir, apply_nodir=False)
    (run_dir / "landuse.parquet").write_bytes(b"data")
    audit_path = tmp_path / "audit.jsonl"
    summary_path = tmp_path / "summary.json"
    approval_file = tmp_path / "approval.md"
    approval_file.write_text("approver: someone\n", encoding="utf-8")

    code = batch_migration.run_batch_migration(
        host="wepp1",
        mode="apply",
        roots_csv=str(tmp_path),
        audit_jsonl=audit_path,
        summary_json=summary_path,
        max_workers=1,
        wepp1_approval_file=approval_file,
        approval_token=None,
    )
    assert code == 2


def test_wepp1_dry_run_does_not_require_approval_file(tmp_path: Path) -> None:
    run_dir = tmp_path / "bb" / "run-g"
    _write_run_config(run_dir, apply_nodir=False)
    (run_dir / "landuse.parquet").write_bytes(b"data")

    audit_path = tmp_path / "audit.jsonl"
    summary_path = tmp_path / "summary.json"
    code = batch_migration.run_batch_migration(
        host="wepp1",
        mode="dry-run",
        roots_csv=str(tmp_path),
        audit_jsonl=audit_path,
        summary_json=summary_path,
        max_workers=1,
        wepp1_approval_file=None,
        approval_token=None,
    )

    assert code == 0
    summary = _read_json(summary_path)
    assert summary["status"] == "ok"
    assert summary["mode"] == "dry-run"


def test_run_batch_summary_and_audit_contract(tmp_path: Path) -> None:
    run_false = tmp_path / "cc" / "run-h"
    _write_run_config(run_false, apply_nodir=False)
    (run_false / "landuse.parquet").write_bytes(b"a")

    run_true = tmp_path / "dd" / "run-i"
    _write_run_config(run_true, apply_nodir=True)
    (run_true / "landuse.parquet").write_bytes(b"b")

    audit_path = tmp_path / "audit.jsonl"
    summary_path = tmp_path / "summary.json"
    code = batch_migration.run_batch_migration(
        host="forest",
        mode="dry-run",
        roots_csv=str(tmp_path),
        audit_jsonl=audit_path,
        summary_json=summary_path,
        max_workers=2,
        wepp1_approval_file=None,
        approval_token=None,
    )

    assert code == 0
    summary = _read_json(summary_path)
    totals = summary["totals"]
    assert isinstance(totals, dict)
    assert totals["runs_discovered"] == 2
    assert totals["runs_processed"] == 2
    assert totals["runs_eligible"] == 1
    assert totals["runs_dry_run"] == 1
    assert totals["runs_skipped"] == 1
    assert totals["files_discovered"] == 2
    assert totals["files_conflict"] == 0

    records = _read_jsonl(audit_path)
    record_types = {record["record_type"] for record in records}
    assert {"root_validation", "file_action", "run_summary"} <= record_types
    assert any(record.get("action") == "planned" for record in records if record.get("record_type") == "file_action")


def test_process_run_with_unresolved_apply_nodir_reports_error(tmp_path: Path) -> None:
    run_dir = tmp_path / "run-j"
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "landuse.parquet").write_bytes(b"data")

    result = batch_migration._process_run(host="forest", mode="dry-run", run_dir=run_dir)
    assert result.final_status == "error"
    assert result.files_error == 1


def test_resolve_apply_nodir_override_and_invalid_override(tmp_path: Path) -> None:
    run_true = tmp_path / "run-p"
    _write_run_config_spec(
        run_true,
        "test.cfg?nodb:apply_nodir=true",
        defaults_text="[nodb]\napply_nodir=false\n",
        cfg_text="[nodb]\napply_nodir=false\n",
    )
    resolved_true = batch_migration.resolve_apply_nodir(run_true)
    assert resolved_true.value is True
    assert resolved_true.source == "cfg_override"

    run_bad = tmp_path / "run-q"
    _write_run_config_spec(
        run_bad,
        "test.cfg?nodb:apply_nodir=maybe",
        defaults_text="[nodb]\napply_nodir=false\n",
        cfg_text="[nodb]\napply_nodir=false\n",
    )
    resolved_bad = batch_migration.resolve_apply_nodir(run_bad)
    assert resolved_bad.value is None
    assert resolved_bad.source == "cfg_override_error"


def test_resolve_apply_nodir_cfg_read_missing_option_and_bad_value(tmp_path: Path) -> None:
    run_missing_cfg = tmp_path / "run-r"
    run_missing_cfg.mkdir(parents=True, exist_ok=True)
    (run_missing_cfg / "_defaults.toml").write_text("[nodb]\napply_nodir=false\n", encoding="utf-8")
    (run_missing_cfg / "ron.nodb").write_text(
        json.dumps({"py/state": {"_config": "missing.cfg"}}),
        encoding="utf-8",
    )
    resolved_missing_cfg = batch_migration.resolve_apply_nodir(run_missing_cfg)
    assert resolved_missing_cfg.value is None
    assert resolved_missing_cfg.source == "cfg_read_error"

    run_missing_opt = tmp_path / "run-s"
    _write_run_config_spec(
        run_missing_opt,
        "test.cfg",
        defaults_text="[nodb]\n# no apply_nodir option\n",
        cfg_text="[nodb]\ndefault_wepp_type = granitic\n",
    )
    resolved_missing_opt = batch_migration.resolve_apply_nodir(run_missing_opt)
    assert resolved_missing_opt.value is None
    assert resolved_missing_opt.source == "cfg_missing_option"

    run_bad_value = tmp_path / "run-t"
    _write_run_config_spec(
        run_bad_value,
        "test.cfg",
        defaults_text="[nodb]\napply_nodir=false\n",
        cfg_text="[nodb]\napply_nodir=invalid_bool\n",
    )
    resolved_bad_value = batch_migration.resolve_apply_nodir(run_bad_value)
    assert resolved_bad_value.value is None
    assert resolved_bad_value.source == "cfg_value_error"


def test_apply_conflict_branch_for_fileexists_race(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    run_dir = tmp_path / "run-k"
    _write_run_config(run_dir, apply_nodir=False)
    (run_dir / "landuse.parquet").write_bytes(b"data")

    def _raise_exists(*_args: object) -> None:
        raise FileExistsError()

    monkeypatch.setattr(batch_migration, "_apply_move", _raise_exists)

    result = batch_migration._process_run(host="forest", mode="apply", run_dir=run_dir)
    assert result.final_status == "conflict_requires_manual_resolution"
    assert result.files_conflict == 1
    assert (run_dir / "landuse.parquet").exists()


def test_apply_lock_contention_reports_error(tmp_path: Path) -> None:
    run_dir = tmp_path / "run-l"
    _write_run_config(run_dir, apply_nodir=False)
    (run_dir / "landuse.parquet").write_bytes(b"data")
    (run_dir / ".root_resource_unroll_batch.lock").write_text("held", encoding="utf-8")

    result = batch_migration._process_run(host="forest", mode="apply", run_dir=run_dir)
    assert result.final_status == "error"
    assert result.files_error == 1


def test_conflict_run_is_idempotent_across_retries(tmp_path: Path) -> None:
    run_dir = tmp_path / "run-m"
    _write_run_config(run_dir, apply_nodir=False)
    (run_dir / "soils.parquet").write_bytes(b"root")
    (run_dir / "soils").mkdir(parents=True, exist_ok=True)
    (run_dir / "soils" / "soils.parquet").write_bytes(b"target")

    first = batch_migration._process_run(host="forest", mode="apply", run_dir=run_dir)
    second = batch_migration._process_run(host="forest", mode="apply", run_dir=run_dir)

    assert first.files_conflict == 1
    assert second.files_conflict == 1
    assert first.final_status == "conflict_requires_manual_resolution"
    assert second.final_status == "conflict_requires_manual_resolution"
    assert (run_dir / "soils.parquet").exists()


def test_missing_source_candidate_is_noop_skip(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    run_dir = tmp_path / "run-u"
    _write_run_config(run_dir, apply_nodir=False)
    candidate = batch_migration.ResourceCandidate("landuse.parquet", "landuse/landuse.parquet", "landuse")
    monkeypatch.setattr(batch_migration, "discover_root_resources", lambda _run_dir: [candidate])

    result = batch_migration._process_run(host="forest", mode="apply", run_dir=run_dir)
    assert result.files_error == 0
    assert result.final_status == "ok"
    file_records = [r for r in result.records if r.get("record_type") == "file_action"]
    assert file_records[0]["status"] == "skipped"


def test_source_hash_enoent_is_noop_skip(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    run_dir = tmp_path / "run-v"
    _write_run_config(run_dir, apply_nodir=False)
    (run_dir / "landuse.parquet").write_bytes(b"data")
    original_hash = batch_migration._sha256_path

    def _enoent_on_source(path: Path) -> str:
        if path.name == "landuse.parquet":
            raise OSError(errno.ENOENT, os.strerror(errno.ENOENT))
        return original_hash(path)

    import errno

    monkeypatch.setattr(batch_migration, "_sha256_path", _enoent_on_source)
    result = batch_migration._process_run(host="forest", mode="dry-run", run_dir=run_dir)
    assert result.files_error == 0
    assert result.final_status == "dry_run"


def test_run_batch_root_validation_error_summary(tmp_path: Path) -> None:
    nondir_path = tmp_path / "not_a_dir.txt"
    nondir_path.write_text("x", encoding="utf-8")
    missing_path = tmp_path / "missing"
    audit_path = tmp_path / "audit.jsonl"
    summary_path = tmp_path / "summary.json"

    code = batch_migration.run_batch_migration(
        host="forest",
        mode="dry-run",
        roots_csv=f"{nondir_path},{missing_path}",
        audit_jsonl=audit_path,
        summary_json=summary_path,
        max_workers=1,
        wepp1_approval_file=None,
        approval_token=None,
    )

    assert code == 2
    summary = _read_json(summary_path)
    assert summary["status"] == "error"
    assert any("not a directory" in msg for msg in summary["errors"])
    assert any("does not exist" in msg for msg in summary["errors"])


def test_run_batch_discovery_oserror_returns_error_summary(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = tmp_path / "root"
    root.mkdir(parents=True, exist_ok=True)
    audit_path = tmp_path / "audit.jsonl"
    summary_path = tmp_path / "summary.json"

    def _raise_discovery(_roots: list[Path]) -> list[Path]:
        raise OSError("discovery failed")

    monkeypatch.setattr(batch_migration, "discover_project_dirs", _raise_discovery)

    code = batch_migration.run_batch_migration(
        host="forest",
        mode="dry-run",
        roots_csv=str(root),
        audit_jsonl=audit_path,
        summary_json=summary_path,
        max_workers=1,
        wepp1_approval_file=None,
        approval_token=None,
    )
    assert code == 2
    summary = _read_json(summary_path)
    assert summary["status"] == "error"
    assert "failed discovering project directories" in summary["errors"][0]


def test_discover_project_dirs_uses_find_fast_paths_and_parses_results(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    runs_root = tmp_path / "runs"
    batch_root = tmp_path / "batch"
    runs_root.mkdir(parents=True, exist_ok=True)
    batch_root.mkdir(parents=True, exist_ok=True)

    class _Result:
        def __init__(self, returncode: int, stdout: str, stderr: str = "") -> None:
            self.returncode = returncode
            self.stdout = stdout
            self.stderr = stderr

    calls: list[list[str]] = []

    def _fake_run(cmd: list[str], check: bool, capture_output: bool, text: bool) -> _Result:
        assert check is False
        assert capture_output is True
        assert text is True
        calls.append(cmd)
        root_path = cmd[1]
        if root_path.endswith("/runs"):
            return _Result(
                0,
                "\n".join(
                    [
                        f"{root_path}/aa/run-one/ron.nodb",
                        f"{root_path}/bb/run-two/ron.nodb",
                    ]
                ),
            )
        return _Result(
            0,
            "\n".join(
                [
                    f"{root_path}/projA/_base/ron.nodb",
                    f"{root_path}/projA/runs/run-three/ron.nodb",
                ]
            ),
        )

    monkeypatch.setattr(batch_migration.subprocess, "run", _fake_run)
    discovered = batch_migration.discover_project_dirs([runs_root, batch_root])

    assert len(calls) == 2
    runs_cmd = calls[0]
    batch_cmd = calls[1]
    assert "-mindepth" in runs_cmd and "-maxdepth" in runs_cmd
    assert "-prune" in batch_cmd
    discovered_paths = [str(path) for path in discovered]
    assert str(runs_root / "aa" / "run-one") in discovered_paths
    assert str(runs_root / "bb" / "run-two") in discovered_paths
    assert str(batch_root / "projA" / "_base") in discovered_paths
    assert str(batch_root / "projA" / "runs" / "run-three") in discovered_paths


def test_main_returns_2_for_invalid_roots_csv(tmp_path: Path) -> None:
    audit_path = tmp_path / "audit.jsonl"
    summary_path = tmp_path / "summary.json"
    code = batch_migration.main(
        [
            "--host",
            "forest",
            "--mode",
            "dry-run",
            "--roots",
            ",",
            "--audit-jsonl",
            str(audit_path),
            "--summary-json",
            str(summary_path),
        ]
    )
    assert code == 2


def test_main_reads_resolved_summary_path_with_tilde(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    home_dir = tmp_path / "home"
    home_dir.mkdir(parents=True, exist_ok=True)
    root = tmp_path / "root"
    root.mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("HOME", str(home_dir))

    code = batch_migration.main(
        [
            "--host",
            "forest",
            "--mode",
            "dry-run",
            "--roots",
            str(root),
            "--audit-jsonl",
            "~/audit.jsonl",
            "--summary-json",
            "~/summary.json",
        ]
    )
    captured = capsys.readouterr()

    assert code == 0
    assert (home_dir / "summary.json").exists()
    assert '"status": "ok"' in captured.out


def test_catalog_refresh_unexpected_exception_is_nonfatal(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_module = types.ModuleType("wepppy.query_engine")

    def _raise_unexpected(*_args: object, **_kwargs: object) -> None:
        raise Exception("unexpected")

    fake_module.update_catalog_entry = _raise_unexpected
    monkeypatch.setitem(sys.modules, "wepppy.query_engine", fake_module)

    note = batch_migration._refresh_query_catalog_entry(tmp_path, "landuse/landuse.parquet")
    assert note.startswith("catalog_refresh=deferred:")


def test_scan_io_error_is_reported_as_run_error(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    run_dir = tmp_path / "run-n"
    _write_run_config(run_dir, apply_nodir=False)
    (run_dir / "landuse.parquet").write_bytes(b"data")

    def _raise_scan_error(_run_dir: Path) -> list[batch_migration.ResourceCandidate]:
        raise PermissionError("no access")

    monkeypatch.setattr(batch_migration, "discover_root_resources", _raise_scan_error)
    result = batch_migration._process_run(host="forest", mode="dry-run", run_dir=run_dir)

    assert result.final_status == "error"
    assert result.files_error == 1


def test_dry_run_hash_errors_set_run_error_status(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    run_dir = tmp_path / "run-o"
    _write_run_config(run_dir, apply_nodir=False)
    (run_dir / "landuse.parquet").write_bytes(b"data")

    def _raise_hash_error(_path: Path) -> str:
        raise OSError("hash failure")

    monkeypatch.setattr(batch_migration, "_sha256_path", _raise_hash_error)
    result = batch_migration._process_run(host="forest", mode="dry-run", run_dir=run_dir)

    assert result.files_error == 1
    assert result.final_status == "error"
