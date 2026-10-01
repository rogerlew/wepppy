import json
import os

import pytest

from wepppy.weppcloud.run_catalog.extractor import extract
from wepppy.weppcloud.run_catalog.paths import Roots

pytestmark = pytest.mark.unit


@pytest.fixture
def project(tmp_path):
    roots = Roots(primary=str(tmp_path / "runs"), legacy=str(tmp_path / "legacy"), batch=str(tmp_path / "batch"))
    directory = tmp_path / "runs" / "te" / "test"
    directory.mkdir(parents=True)
    return roots, directory


def write_ron(directory, **values):
    (directory / "ron.nodb").write_text(json.dumps({"_name": "", "_scenario": "", "_map": None, **values}))


@pytest.mark.parametrize("alias", [False, True])
def test_readonly_absolute_project_directory(project, tmp_path, alias):
    roots, directory = project
    write_ron(directory)
    if alias:
        linked = tmp_path / "alias"
        linked.symlink_to(roots.primary)
        roots = Roots(primary=str(linked), legacy=roots.legacy)
        target = linked / "te" / "test"
    else:
        target = directory
    (directory / "READONLY").symlink_to(target)
    assert extract("test", roots).sources["readonly"].values == {"readonly": True}


@pytest.mark.parametrize("kind,subdirectory", [("omni", "scenarios"), ("omni-contrast", "contrasts")])
def test_profile_named_parent_supports_omni(project, kind, subdirectory):
    roots, directory = project
    child = directory.parents[1] / "pr" / "profile" / "_pups" / "omni" / subdirectory / "leaf"
    child.mkdir(parents=True)
    write_ron(child, _name="Profile child")
    assert extract("profile;;" + kind + ";;leaf", roots).sources["ron"].values["name"] == "Profile child"


def test_empty_missing_optional_and_no_repair(project):
    roots, directory = project
    write_ron(directory)
    (directory / "climate").symlink_to("missing")
    before = sorted((entry.name, entry.lstat().st_mtime_ns) for entry in directory.iterdir())
    snapshot = extract("test", roots)
    assert snapshot.sources["ron"].values["name"] == ""
    assert snapshot.sources["readonly"].values == {"readonly": False}
    assert snapshot.sources["ttl"].state == "missing"
    assert before == sorted((entry.name, entry.lstat().st_mtime_ns) for entry in directory.iterdir())


@pytest.mark.parametrize("center", [[-116, 46], {"py/tuple": [-116, 46]}])
def test_legacy_map_and_ttl_normalization(project, center):
    roots, directory = project
    write_ron(directory, _name="Legacy", _map={"py/object": "wepppy.nodb.ron.Map", "center": center, "zoom": 10})
    (directory / "TTL").write_text('{"expires_at":"2030-01-01T00:00:00Z"}')
    snapshot = extract("test", roots)
    assert snapshot.sources["ron"].values["map_lng"] == -116
    assert snapshot.sources["ttl"].values["ttl_policy"] == "rolling_90d"
    assert snapshot.sources["ttl"].values["ttl_deletion_at"].year == 2030


def test_no_reconstruction_and_invalid_ron(project):
    roots, directory = project
    (directory / "ron.nodb").write_text('{"py/reduce":[{"py/function":"os.system"}, {"py/tuple":["false"]}]}')
    assert extract("test", roots).sources["ron"].state == "invalid"


def test_leaf_cross_project_rejected_same_project_supported(project, tmp_path):
    roots, directory = project
    other = tmp_path / "other"
    other.mkdir()
    write_ron(other, _name="secret")
    (directory / "ron.nodb").symlink_to(other / "ron.nodb")
    observation = extract("test", roots).sources["ron"]
    assert observation.state == "unreadable"
    assert observation.error == "source_scope_mismatch"
    (directory / "ron.nodb").unlink()
    (directory / "metadata").write_text('{"_name":"safe"}')
    (directory / "ron.nodb").symlink_to("metadata")
    assert extract("test", roots).sources["ron"].values["name"] == "safe"


def test_ancestor_redirect_rejected(project, tmp_path):
    roots, directory = project
    directory.rmdir()
    directory.symlink_to(tmp_path, target_is_directory=True)
    assert extract("test", roots).sources["ron"].error == "source_scope_mismatch"


def test_legacy_and_grouped_roots(project, tmp_path):
    roots, directory = project
    legacy = tmp_path / "legacy" / "older"
    legacy.mkdir(parents=True)
    write_ron(legacy)
    assert extract("older", roots).sources["ron"].state == "ready"
    child = directory / "_pups" / "omni" / "scenarios" / "burned"
    child.mkdir(parents=True)
    write_ron(child)
    assert extract("test;;omni;;burned", roots).sources["ron"].state == "ready"
    assert not (child / "climate").exists()
    assert roots.matches("test;;omni;;burned", str(child))
    assert not roots.matches("test", str(child))


def test_offline_same_size_restored_mtime_is_read(project):
    roots, directory = project
    write_ron(directory, _name="first")
    source = directory / "ron.nodb"
    stamp = source.stat()
    before = extract("test", roots)
    write_ron(directory, _name="other")
    os.utime(source, ns=(stamp.st_atime_ns, stamp.st_mtime_ns))
    after = extract("test", roots)
    assert before.sources["ron"].version["sha256"] != after.sources["ron"].version["sha256"]


@pytest.mark.parametrize("runid", ["../escape", "bad;;omni;;..", "unknown;;group;;leaf"])
def test_reject_invalid_identity(project, runid):
    roots, directory = project
    assert extract(runid, roots).sources["ron"].error == "source_scope_mismatch"


def test_actual_current_ron_serialization(project):
    import jsonpickle
    from wepppy.nodb.core.ron import Ron
    roots, directory = project
    ron = object.__new__(Ron)
    ron.__dict__.update(_name="Actual serialized project", _scenario="", _map=None, wd=str(directory))
    payload = jsonpickle.encode(ron)
    assert "py/state" in payload
    (directory / "ron.nodb").write_text(payload)
    assert extract("test", roots).sources["ron"].values["name"] == ron.name


@pytest.mark.parametrize("runid", ["..outside", "..outside;;omni;;leaf"])
def test_generated_dotdot_prefix_never_reads_outside(project, runid):
    roots, directory = project
    assert extract(runid, roots).sources["ron"].error == "source_scope_mismatch"


def test_batch_named_omni_keeps_batch_precedence(project, tmp_path):
    roots, directory = project
    batch = tmp_path / "batch" / "omni" / "runs" / "leaf"
    batch.mkdir(parents=True)
    write_ron(batch, _name="batch")
    assert extract("batch;;omni;;leaf", roots).sources["ron"].values["name"] == "batch"


def test_readonly_unreadable_contents_still_present(project):
    roots, directory = project
    write_ron(directory)
    marker = directory / "READONLY"
    marker.write_text("private")
    marker.chmod(0)
    try:
        assert extract("test", roots).sources["readonly"].values == {"readonly": True}
    finally:
        marker.chmod(0o600)


def test_symlink_dotdot_uses_filesystem_order(project):
    roots, directory = project
    (directory / "nested" / "inner").mkdir(parents=True)
    (directory / "shortcut").symlink_to("nested/inner", target_is_directory=True)
    (directory / "metadata").write_text('{"_name":"wrong"}')
    (directory / "nested" / "metadata").write_text('{"_name":"correct"}')
    (directory / "ron.nodb").symlink_to("shortcut/../metadata")
    assert extract("test", roots).sources["ron"].values["name"] == "correct"


def test_absolute_source_link_through_trusted_root_alias(project, tmp_path):
    from dataclasses import replace
    roots, directory = project
    alias = tmp_path / "alias"
    alias.symlink_to(roots.primary, target_is_directory=True)
    roots = replace(roots, primary=str(alias))
    (directory / "metadata").write_text('{"_name":"same-project"}')
    (directory / "ron.nodb").symlink_to(alias / "te" / "test" / "metadata")
    assert extract("test", roots).sources["ron"].values["name"] == "same-project"


def test_removed_binding_is_retry_not_missing(project, monkeypatch):
    from wepppy.weppcloud.run_catalog import extractor
    roots, directory = project
    write_ron(directory)
    original = extractor._observe
    removed = False

    def remove_after_read(*args, **kwargs):
        nonlocal removed
        observation = original(*args, **kwargs)
        if not removed:
            directory.rename(directory.with_name("moved"))
            removed = True
        return observation

    monkeypatch.setattr(extractor, "_observe", remove_after_read)
    assert extract("test", roots).sources["ron"].state == "unreadable"


def test_ancestor_replacement_preserving_project_inode_is_drift(project, monkeypatch):
    from wepppy.weppcloud.run_catalog import extractor
    roots, directory = project
    write_ron(directory)
    original = extractor._observe
    changed = False

    def replace_parent(*args, **kwargs):
        nonlocal changed
        observation = original(*args, **kwargs)
        if not changed:
            parent = directory.parent
            old_parent = parent.with_name("old-parent")
            parent.rename(old_parent)
            parent.mkdir()
            (old_parent / directory.name).rename(directory)
            changed = True
        return observation

    monkeypatch.setattr(extractor, "_observe", replace_parent)
    assert extract("test", roots).sources["ron"].state == "unreadable"


def test_omni_does_not_inherit_playback_precedence(project, tmp_path):
    from dataclasses import replace
    roots, directory = project
    roots = replace(roots, profile_runs=str(tmp_path / "playback"), playback_clone=True)
    for base, name in ((directory, "primary"), (tmp_path / "playback" / "test", "clone")):
        child = base / "_pups" / "omni" / "scenarios" / "burned"
        child.mkdir(parents=True)
        write_ron(child, _name=name)
    assert extract("test;;omni;;burned", roots).sources["ron"].values["name"] == "primary"


def test_primary_appearance_invalidates_legacy_binding(project, tmp_path, monkeypatch):
    from wepppy.weppcloud.run_catalog import extractor
    roots, directory = project
    directory.rmdir()
    legacy = tmp_path / "legacy" / "test"
    legacy.mkdir(parents=True)
    write_ron(legacy, _name="old")
    original = extractor._observe
    changed = False

    def create_primary(*args, **kwargs):
        nonlocal changed
        observation = original(*args, **kwargs)
        if not changed:
            directory.mkdir()
            write_ron(directory, _name="new")
            changed = True
        return observation

    monkeypatch.setattr(extractor, "_observe", create_primary)
    assert extract("test", roots).sources["ron"].state == "unreadable"
