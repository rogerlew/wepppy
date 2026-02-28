import os
import types

import pytest

from wepppy.weppcloud.utils import helpers


pytestmark = pytest.mark.unit


def _disable_redis_cache(monkeypatch: pytest.MonkeyPatch) -> None:
    """Avoid touching real Redis during path resolution tests."""
    monkeypatch.setattr(helpers, "redis_wd_cache_client", None)


def test_get_wd_prefers_primary_when_both_exist(monkeypatch: pytest.MonkeyPatch) -> None:
    _disable_redis_cache(monkeypatch)
    runid = "ab-newrun"

    def fake_exists(path: str) -> bool:
        if path == "/wc1/runs/ab/ab-newrun":
            return True
        if path == "/geodata/weppcloud_runs/ab-newrun":
            return True
        return False

    monkeypatch.setattr(helpers, "_exists", fake_exists)

    resolved = helpers.get_wd(runid, prefer_active=False)

    assert resolved == "/wc1/runs/ab/ab-newrun"


def test_batch_runs_use_wc1_batch(monkeypatch: pytest.MonkeyPatch) -> None:
    _disable_redis_cache(monkeypatch)
    dummy_app = types.SimpleNamespace(config={})
    monkeypatch.setattr(helpers, "current_app", dummy_app)

    resolved = helpers.get_batch_run_wd("demo-batch", "demo-run")

    assert resolved == "/wc1/batch/demo-batch/runs/demo-run"


def test_get_wd_falls_back_to_legacy_when_primary_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    _disable_redis_cache(monkeypatch)
    runid = "cd-legacy"

    def fake_exists(path: str) -> bool:
        if path == "/wc1/runs/cd/cd-legacy":
            return False
        if path == "/geodata/weppcloud_runs/cd-legacy":
            return True
        return False

    monkeypatch.setattr(helpers, "_exists", fake_exists)

    resolved = helpers.get_wd(runid, prefer_active=False)

    assert resolved == "/geodata/weppcloud_runs/cd-legacy"


def test_get_primary_wd_always_points_to_wc1(monkeypatch: pytest.MonkeyPatch) -> None:
    _disable_redis_cache(monkeypatch)
    runid = "ef-new"
    assert helpers.get_primary_wd(runid) == "/wc1/runs/ef/ef-new"


def test_get_wd_resolves_batch_run(monkeypatch: pytest.MonkeyPatch) -> None:
    _disable_redis_cache(monkeypatch)
    dummy_app = types.SimpleNamespace(config={})
    monkeypatch.setattr(helpers, "current_app", dummy_app)

    resolved = helpers.get_wd("batch;;spring-2025;;run-001", prefer_active=False)

    assert resolved == "/wc1/batch/spring-2025/runs/run-001"


def test_get_wd_resolves_batch_base(monkeypatch: pytest.MonkeyPatch) -> None:
    _disable_redis_cache(monkeypatch)
    dummy_app = types.SimpleNamespace(config={})
    monkeypatch.setattr(helpers, "current_app", dummy_app)

    resolved = helpers.get_wd("batch;;spring-2025;;_base", prefer_active=False)

    assert resolved == "/wc1/batch/spring-2025/_base"


def test_get_wd_resolves_culvert_run(monkeypatch: pytest.MonkeyPatch) -> None:
    _disable_redis_cache(monkeypatch)
    monkeypatch.setenv("CULVERTS_ROOT", "/culverts")

    resolved = helpers.get_wd("culvert;;6d2a2c2b;;pt-001", prefer_active=False)

    assert resolved == "/culverts/6d2a2c2b/runs/pt-001"


def test_get_wd_resolves_profile_run_slugs(monkeypatch: pytest.MonkeyPatch) -> None:
    _disable_redis_cache(monkeypatch)
    monkeypatch.setenv("PROFILE_PLAYBACK_BASE", "/playback")
    monkeypatch.delenv("PROFILE_PLAYBACK_RUN_ROOT", raising=False)
    monkeypatch.delenv("PROFILE_PLAYBACK_FORK_ROOT", raising=False)
    monkeypatch.delenv("PROFILE_PLAYBACK_ARCHIVE_ROOT", raising=False)

    tmp_resolved = helpers.get_wd("profile;;tmp;;playback-01", prefer_active=False)
    assert tmp_resolved == "/playback/runs/playback-01"

    fork_resolved = helpers.get_wd("profile;;fork;;playback-01", prefer_active=False)
    assert fork_resolved == "/playback/fork/playback-01"

    archive_resolved = helpers.get_wd("profile;;archive;;playback-01", prefer_active=False)
    assert archive_resolved == "/playback/archive/playback-01"


def test_get_wd_resolves_omni_scenario_slug(monkeypatch: pytest.MonkeyPatch) -> None:
    _disable_redis_cache(monkeypatch)
    monkeypatch.setattr(helpers, "_exists", lambda _path: False)

    resolved = helpers.get_wd("decimal-pleasing;;omni;;burned", prefer_active=False)

    assert resolved == "/wc1/runs/de/decimal-pleasing/_pups/omni/scenarios/burned"


def test_get_wd_resolves_omni_contrast_slug(monkeypatch: pytest.MonkeyPatch) -> None:
    _disable_redis_cache(monkeypatch)
    monkeypatch.setattr(helpers, "_exists", lambda _path: False)

    resolved = helpers.get_wd("decimal-pleasing;;omni-contrast;;12", prefer_active=False)

    assert resolved == "/wc1/runs/de/decimal-pleasing/_pups/omni/contrasts/12"


def test_get_wd_resolves_nested_batch_omni_scenario(monkeypatch: pytest.MonkeyPatch) -> None:
    _disable_redis_cache(monkeypatch)
    dummy_app = types.SimpleNamespace(config={})
    monkeypatch.setattr(helpers, "current_app", dummy_app)
    monkeypatch.setattr(helpers, "_exists", lambda _path: False)
    ensured: list[tuple[str, str]] = []
    monkeypatch.setattr(
        helpers,
        "_ensure_omni_shared_inputs",
        lambda base_root, run_root: ensured.append((base_root, run_root)),
    )

    resolved = helpers.get_wd("batch;;spring-2025;;run-001;;omni;;treated", prefer_active=False)

    assert resolved == "/wc1/batch/spring-2025/runs/run-001/_pups/omni/scenarios/treated"
    assert ensured == [
        (
            "/wc1/batch/spring-2025/runs/run-001",
            "/wc1/batch/spring-2025/runs/run-001/_pups/omni/scenarios/treated",
        )
    ]


def test_get_wd_resolves_nested_batch_omni_contrast(monkeypatch: pytest.MonkeyPatch) -> None:
    _disable_redis_cache(monkeypatch)
    dummy_app = types.SimpleNamespace(config={})
    monkeypatch.setattr(helpers, "current_app", dummy_app)
    monkeypatch.setattr(helpers, "_exists", lambda _path: False)
    ensured: list[tuple[str, str]] = []
    monkeypatch.setattr(
        helpers,
        "_ensure_omni_shared_inputs",
        lambda base_root, run_root: ensured.append((base_root, run_root)),
    )

    resolved = helpers.get_wd("batch;;spring-2025;;run-001;;omni-contrast;;3", prefer_active=False)

    assert resolved == "/wc1/batch/spring-2025/runs/run-001/_pups/omni/contrasts/3"
    assert ensured == [
        (
            "/wc1/batch/spring-2025/runs/run-001",
            "/wc1/batch/spring-2025/runs/run-001/_pups/omni/contrasts/3",
        )
    ]


def test_get_wd_rejects_malformed_composite_slugs(monkeypatch: pytest.MonkeyPatch) -> None:
    _disable_redis_cache(monkeypatch)
    dummy_app = types.SimpleNamespace(config={})
    monkeypatch.setattr(helpers, "current_app", dummy_app)

    with pytest.raises(ValueError, match="Invalid run identifier"):
        helpers.get_wd("..", prefer_active=False)

    with pytest.raises(ValueError, match="Invalid grouped run identifier"):
        helpers.get_wd("batch;;spring-2025;;run-001;;omni", prefer_active=False)

    with pytest.raises(ValueError, match="Invalid grouped run identifier"):
        helpers.get_wd("batch;;spring-2025;;run-001;;not-supported;;treated", prefer_active=False)

    with pytest.raises(ValueError, match="Invalid grouped run identifier"):
        helpers.get_wd("batch;;;;run-001;;omni;;treated", prefer_active=False)

    with pytest.raises(ValueError, match="Invalid grouped run identifier"):
        helpers.get_wd("batch;;spring-2025;;run-001;;omni;;", prefer_active=False)

    with pytest.raises(ValueError, match="Invalid grouped run identifier"):
        helpers.get_wd("batch;;spring-2025;;run-001;;omni;;..", prefer_active=False)

    # Nested omni suffixes are not supported for non-batch composite parents.
    with pytest.raises(ValueError, match="Invalid grouped run identifier"):
        helpers.get_wd("culvert;;6d2a2c2b;;pt-001;;omni;;treated", prefer_active=False)


@pytest.mark.skipif(not hasattr(os, "symlink"), reason="symlink not supported")
def test_ensure_omni_shared_inputs_links_directory_roots(tmp_path, monkeypatch: pytest.MonkeyPatch) -> None:
    _disable_redis_cache(monkeypatch)
    base_root = tmp_path / "base"
    scenario_root = tmp_path / "scenario"
    base_root.mkdir()
    scenario_root.mkdir()

    (base_root / "climate").mkdir()
    (base_root / "watershed").mkdir()
    (base_root / "dem").mkdir()
    (base_root / "climate.wepp_cli.parquet").write_text("retired", encoding="utf-8")
    (base_root / "watershed.hillslopes.parquet").write_text("retired", encoding="utf-8")
    (base_root / "watershed.channels.parquet").write_text("retired", encoding="utf-8")

    helpers._ensure_omni_shared_inputs(str(base_root), str(scenario_root))
    helpers._ensure_omni_shared_inputs(str(base_root), str(scenario_root))

    assert (scenario_root / "climate").is_symlink()
    assert (scenario_root / "watershed").is_symlink()
    assert (scenario_root / "dem").is_symlink()
    assert os.readlink(scenario_root / "climate") == str(base_root / "climate")
    assert os.readlink(scenario_root / "watershed") == str(base_root / "watershed")
    assert not (scenario_root / "climate.wepp_cli.parquet").exists()
    assert not (scenario_root / "watershed.hillslopes.parquet").exists()
    assert not (scenario_root / "watershed.channels.parquet").exists()


@pytest.mark.skipif(not hasattr(os, "symlink"), reason="symlink not supported")
def test_ensure_omni_shared_inputs_links_nodir_archives(tmp_path, monkeypatch: pytest.MonkeyPatch) -> None:
    _disable_redis_cache(monkeypatch)
    base_root = tmp_path / "base"
    scenario_root = tmp_path / "scenario"
    base_root.mkdir()
    scenario_root.mkdir()

    (base_root / "climate.nodir").write_text("archive", encoding="utf-8")
    (base_root / "watershed.nodir").write_text("archive", encoding="utf-8")
    (base_root / "dem").mkdir()

    helpers._ensure_omni_shared_inputs(str(base_root), str(scenario_root))
    helpers._ensure_omni_shared_inputs(str(base_root), str(scenario_root))

    assert (scenario_root / "climate.nodir").is_symlink()
    assert (scenario_root / "watershed.nodir").is_symlink()
    assert (scenario_root / "dem").is_symlink()
    assert os.readlink(scenario_root / "climate.nodir") == str(base_root / "climate.nodir")
    assert os.readlink(scenario_root / "watershed.nodir") == str(base_root / "watershed.nodir")
    assert not (scenario_root / "climate.wepp_cli.parquet").exists()
    assert not (scenario_root / "watershed.hillslopes.parquet").exists()
    assert not (scenario_root / "watershed.channels.parquet").exists()


@pytest.mark.skipif(not hasattr(os, "symlink"), reason="symlink not supported")
def test_ensure_omni_shared_inputs_preserves_existing_directory_conflicts(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _disable_redis_cache(monkeypatch)
    base_root = tmp_path / "base"
    scenario_root = tmp_path / "scenario"
    base_root.mkdir()
    scenario_root.mkdir()

    (base_root / "climate").mkdir()
    (base_root / "watershed").mkdir()
    (base_root / "dem").mkdir()

    # Simulate an existing non-symlink destination that should not be replaced.
    (scenario_root / "climate").mkdir()

    helpers._ensure_omni_shared_inputs(str(base_root), str(scenario_root))

    assert (scenario_root / "climate").is_dir()
    assert not (scenario_root / "climate").is_symlink()
    assert (scenario_root / "watershed").is_symlink()
    assert (scenario_root / "dem").is_symlink()
