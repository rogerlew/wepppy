import hashlib
import json
import os
import stat
from contextlib import contextmanager

import pytest

from tools.security import import_dependency_evidence as importer


pytestmark = pytest.mark.unit
IMAGE = "sha256:" + "a" * 64


@pytest.fixture
def bundle(tmp_path):
    source = tmp_path / "source"
    source.mkdir()
    store = tmp_path / "store"
    store.mkdir(mode=0o700)
    payload = b'{"matches": [], "purpose": "import integrity fixture only"}\n'
    (source / "scan.json").write_bytes(payload)
    manifest = {"schema_version": 1, "image_id": IMAGE, "files": {
        "scan.json": {"sha256": hashlib.sha256(payload).hexdigest(),
                      "size_bytes": len(payload)}}}
    return source, store, manifest


def write_manifest(source, manifest):
    raw = json.dumps(manifest).encode()
    (source / "manifest.json").write_bytes(raw)
    return hashlib.sha256(raw).hexdigest()


def test_import_retains_exact_bytes_with_private_modes_and_never_overwrites(bundle):
    source, store, manifest = bundle
    digest = write_manifest(source, manifest)
    target = importer.import_bundle(source, store, digest, IMAGE)
    assert target == store / digest / "bundle"
    for name in ("scan.json", "manifest.json"):
        assert (target / name).read_bytes() == (source / name).read_bytes()
        assert stat.S_IMODE((target / name).stat().st_mode) == 0o600
    assert stat.S_IMODE(target.stat().st_mode) == 0o700
    assert stat.S_IMODE(target.parent.stat().st_mode) == 0o700
    with pytest.raises(FileExistsError):
        importer.import_bundle(source, store, digest, IMAGE)
    assert (target / "scan.json").read_bytes() == (source / "scan.json").read_bytes()


@pytest.mark.parametrize("fault", ["hash", "size", "missing", "extra", "symlink", "directory", "fifo"])
def test_invalid_artifact_never_publishes_and_cleans_own_reservation(bundle, fault):
    source, store, manifest = bundle
    unrelated = store / "retained-existing"
    unrelated.mkdir()
    (unrelated / "keep").write_text("preserve")
    artifact = source / "scan.json"
    if fault == "hash":
        artifact.write_bytes(b"x" * artifact.stat().st_size)
    elif fault == "size":
        artifact.write_bytes(b"short")
    elif fault == "missing":
        artifact.unlink()
    elif fault == "extra":
        (source / "extra").write_text("unexpected")
    else:
        artifact.unlink()
        if fault == "symlink":
            artifact.symlink_to(unrelated / "keep")
        elif fault == "directory":
            artifact.mkdir()
        elif fault == "fifo":
            os.mkfifo(artifact)
    digest = write_manifest(source, manifest)
    with pytest.raises((importer.EvidenceError, OSError)):
        importer.import_bundle(source, store, digest, IMAGE)
    assert list(store.iterdir()) == [unrelated]
    assert (unrelated / "keep").read_text() == "preserve"


@pytest.mark.parametrize("name", ["../outside", "/outside", ".", "..", "sub/file", "manifest.json", "x\nname"])
def test_manifest_paths_cannot_escape_the_bundle(bundle, name):
    source, store, manifest = bundle
    manifest["files"][name] = manifest["files"].pop("scan.json")
    digest = write_manifest(source, manifest)
    with pytest.raises(importer.EvidenceError, match="filename"):
        importer.import_bundle(source, store, digest, IMAGE)
    assert not list(store.iterdir())


@pytest.mark.parametrize("fault", ["empty", "boolean_size", "negative_size", "extra_field", "schema", "image", "hash"])
def test_schema_and_trusted_identity_rejections(bundle, fault):
    source, store, manifest = bundle
    if fault == "empty":
        manifest["files"] = {}
    elif fault == "boolean_size":
        manifest["files"]["scan.json"]["size_bytes"] = True
    elif fault == "negative_size":
        manifest["files"]["scan.json"]["size_bytes"] = -1
    elif fault == "extra_field":
        manifest["approved"] = True
    elif fault == "schema":
        manifest["schema_version"] = True
    elif fault == "image":
        manifest["image_id"] = "sha256:" + "b" * 64
    digest = write_manifest(source, manifest)
    if fault == "hash":
        digest = "0" * 64
    with pytest.raises(importer.EvidenceError):
        importer.import_bundle(source, store, digest, IMAGE)
    assert not list(store.iterdir())


def test_duplicate_json_keys_are_rejected_even_with_matching_hash(bundle):
    source, store, _ = bundle
    raw = b'{"schema_version":1,"schema_version":1}'
    (source / "manifest.json").write_bytes(raw)
    with pytest.raises(importer.EvidenceError, match="duplicate JSON key"):
        importer.import_bundle(source, store, hashlib.sha256(raw).hexdigest(), IMAGE)


def test_shared_store_permissions_fail_before_writes(bundle):
    source, store, manifest = bundle
    digest = write_manifest(source, manifest)
    store.chmod(0o750)
    with pytest.raises(importer.EvidenceError, match="mode 0700"):
        importer.import_bundle(source, store, digest, IMAGE)
    assert not list(store.iterdir())


def test_root_alias_is_supported_but_bundle_symlinks_are_not(bundle, tmp_path):
    source, store, manifest = bundle
    digest = write_manifest(source, manifest)
    alias = tmp_path / "store-alias"
    alias.symlink_to(store, target_is_directory=True)
    target = importer.import_bundle(source, alias, digest, IMAGE)
    assert target == store / digest / "bundle"
    assert (target / "scan.json").read_bytes() == (source / "scan.json").read_bytes()


def test_copy_failure_removes_only_new_import(bundle, monkeypatch):
    source, store, manifest = bundle
    digest = write_manifest(source, manifest)

    def fail_copy(*args):
        raise OSError("injected write failure")

    monkeypatch.setattr(importer, "_copy_artifact", fail_copy)
    with pytest.raises(OSError, match="injected write failure"):
        importer.import_bundle(source, store, digest, IMAGE)
    assert not list(store.iterdir())


def test_source_mutation_is_rejected_even_when_already_read_bytes_match(bundle, monkeypatch):
    source, store, manifest = bundle
    digest = write_manifest(source, manifest)
    original_reader = importer._read_file

    class MutatingReader:
        def __init__(self, reader):
            self.reader = reader
            self.changed = False

        def fileno(self):
            return self.reader.fileno()

        def read(self, size):
            chunk = self.reader.read(size)
            if chunk and not self.changed:
                artifact = source / "scan.json"
                before = artifact.stat()
                with artifact.open("r+b") as writer:
                    writer.write(b"X")
                os.utime(artifact, ns=(before.st_atime_ns, before.st_mtime_ns + 1_000_000_000))
                self.changed = True
            return chunk

    @contextmanager
    def reader_with_mutation(directory, name):
        with original_reader(directory, name) as reader:
            yield MutatingReader(reader) if name == "scan.json" else reader

    monkeypatch.setattr(importer, "_read_file", reader_with_mutation)
    with pytest.raises(importer.EvidenceError, match="changed during import"):
        importer.import_bundle(source, store, digest, IMAGE)
    assert not list(store.iterdir())


def test_changed_root_alias_does_not_change_reported_retention_path(bundle, tmp_path, monkeypatch):
    source, store, manifest = bundle
    digest = write_manifest(source, manifest)
    alternate = tmp_path / "alternate"
    alternate.mkdir(mode=0o700)
    alias = tmp_path / "alias"
    alias.symlink_to(store, target_is_directory=True)
    original_copy = importer._copy_artifact

    def copy_and_change_alias(*args):
        original_copy(*args)
        alias.unlink()
        alias.symlink_to(alternate, target_is_directory=True)

    monkeypatch.setattr(importer, "_copy_artifact", copy_and_change_alias)
    target = importer.import_bundle(source, alias, digest, IMAGE)
    assert target == store / digest / "bundle"
    assert (target / "scan.json").read_bytes() == (source / "scan.json").read_bytes()
    assert not list(alternate.iterdir())


@pytest.mark.parametrize("failure_call", [4, 5])
def test_directory_sync_failure_after_rename_removes_failed_bundle(bundle, monkeypatch, failure_call):
    source, store, manifest = bundle
    digest = write_manifest(source, manifest)
    original_fsync = os.fsync
    calls = 0

    def fail_directory_sync(descriptor):
        nonlocal calls
        calls += 1
        if calls == failure_call:
            raise OSError("injected durability failure")
        original_fsync(descriptor)

    monkeypatch.setattr(importer.os, "fsync", fail_directory_sync)
    with pytest.raises(OSError, match="injected durability failure"):
        importer.import_bundle(source, store, digest, IMAGE)
    assert calls == failure_call
    assert not list(store.iterdir())


def test_cli_reports_retention_not_approval(bundle, capsys):
    source, store, manifest = bundle
    digest = write_manifest(source, manifest)
    assert importer.main(["--source", str(source), "--store", str(store),
                          "--expected-manifest-sha256", digest,
                          "--expected-image-id", IMAGE]) == 0
    assert json.loads(capsys.readouterr().out)["status"] == "retained-not-approved"
