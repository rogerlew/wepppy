"""Characterize native work-product retention on actual helper packaging error."""
import errno
import json
from pathlib import Path

import pytest

from tests.nodb.mods.test_features_export_freshness import export_source, _execute
from wepppy.nodb.mods.features_export import service
from wepppy.nodb.mods.features_export.exporters import geodatabase


def test_actual_native_gdb_packaging_error_retains_work(tmp_path, export_source, monkeypatch):
    original = _execute(tmp_path, "producer", "geopackage")
    observed = {}

    def fail_packaging(base_name, *args, **kwargs):
        # Native ogr2ogr has already created the real GDB before this seam.
        output = Path(base_name)
        native_files = [path for path in output.rglob("*") if path.is_file()]
        observed["native_file_count_before_error"] = len(native_files)
        observed["native_bytes_before_error"] = sum(path.stat().st_size for path in native_files)
        observed["native_paths"] = [str(path.relative_to(tmp_path)) for path in native_files]
        partial_zip = output.with_suffix(output.suffix + ".zip")
        partial_zip.write_bytes(b"review-injected partial archive")
        observed["partial_zip"] = str(partial_zip.relative_to(tmp_path))
        raise OSError(errno.ENOSPC, "review-injected failure after real native output")

    monkeypatch.setattr(geodatabase.shutil, "make_archive", fail_packaging)
    with pytest.raises(geodatabase.FeaturesExportWriterError):
        service.co_create_post_wepp_geodatabase_artifact(
            tmp_path, source_job_id="producer", source_job_result=original,
        )
    observed["remaining_native_paths"] = [
        path for path in observed["native_paths"] if (tmp_path / path).exists()
    ]
    observed["partial_zip_retained"] = (tmp_path / observed["partial_zip"]).exists()
    observed["failed_manifests"] = [
        json.loads(path.read_text())
        for path in (tmp_path / "export/features/artifacts").glob("*/manifest.json")
        if json.loads(path.read_text()).get("dependency_verification", {}).get("status") == "error"
    ]
    print(json.dumps(observed, indent=2))
    assert observed["native_file_count_before_error"] > 0
    assert observed["remaining_native_paths"] == []
    assert observed["partial_zip_retained"] is False
    assert len(observed["failed_manifests"]) == 1
