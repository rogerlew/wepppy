"""Actual native generation changes, restored bytes, and content-key reuse."""
import errno
import json
import os
from pathlib import Path

from osgeo import gdal
import pytest

from raster_implementation_security_probe import raster
from wepppy.all_your_base import raster_freshness as freshness
from wepppy.nodb.mods.baer import sbs_map


def retain(name, result):
    Path(__file__).with_name(f"raster_read_guard_security_{name}.json").write_text(json.dumps(result, indent=2)+"\n")
    print("READ_GUARD " + json.dumps({"case": name, **result}))


@pytest.mark.parametrize("kind", ["bytes_restored", "temporary_pam"])
def test_intermediate_native_generation_is_not_admitted(tmp_path, monkeypatch, kind):
    source = tmp_path / "source.tif"
    raster(source)
    original_bytes = source.read_bytes()
    original_stat = source.stat()
    before = freshness.observe_raster_dependencies((source,))
    native = sbs_map._summarize_sbs_raster_rust
    expected = native(str(source))
    observed = []
    sbs_map._summarize_sbs_raster_cached.cache_clear()

    def change_read_restore(path):
        pam = Path(str(source)+".aux.xml")
        try:
            if kind == "bytes_restored":
                dataset = gdal.Open(str(source), gdal.GA_Update)
                dataset.GetRasterBand(1).Fill(3)
                dataset = None
            else:
                pam.write_text('<PAMDataset><PAMRasterBand band="1"><NoDataValue>1</NoDataValue></PAMRasterBand></PAMDataset>')
            result = native(path)
            observed.append(result)
            return result
        finally:
            if kind == "bytes_restored":
                source.write_bytes(original_bytes)
                os.utime(source, ns=(original_stat.st_atime_ns, original_stat.st_mtime_ns))
            else:
                pam.unlink()

    monkeypatch.setattr(sbs_map, "_summarize_sbs_raster_rust", change_read_restore)
    with pytest.raises(OSError) as caught:
        sbs_map._summarize_sbs_raster(str(source))
    after = freshness.observe_raster_dependencies((source,))
    retain(kind, {"errno": caught.value.errno, "same_content_identity": before == after,
                  "different_guard": before.read_guard != after.read_guard,
                  "original_native": expected, "intermediate_native": observed,
                  "cache_entries": sbs_map._summarize_sbs_raster_cached.cache_info().currsize})
    assert caught.value.errno == errno.ESTALE
    assert before == after
    assert before.read_guard != after.read_guard
    assert observed and observed[0] != expected
    assert sbs_map._summarize_sbs_raster_cached.cache_info().currsize == 0


def test_completed_metadata_changes_preserve_numerical_cache_key(tmp_path, monkeypatch):
    source = tmp_path / "source.tif"
    raster(source)
    native = sbs_map._summarize_sbs_raster_rust
    calls = []
    sbs_map._summarize_sbs_raster_cached.cache_clear()

    def counted(path):
        calls.append(path)
        return native(path)

    monkeypatch.setattr(sbs_map, "_summarize_sbs_raster_rust", counted)
    first = sbs_map._summarize_sbs_raster(str(source))
    before = freshness.observe_raster_dependencies((source,))
    alias = tmp_path / "ordinary-link"
    os.link(source, alias)
    alias.unlink()
    source.chmod(0o640)
    after = freshness.observe_raster_dependencies((source,))
    second = sbs_map._summarize_sbs_raster(str(source))
    retain("completed_metadata", {"native_calls": len(calls), "cache_hits": sbs_map._summarize_sbs_raster_cached.cache_info().hits,
                                 "same_identity": before == after, "same_hash": hash(before) == hash(after),
                                 "different_guard": before.read_guard != after.read_guard})
    assert first == second
    assert len(calls) == 1
    assert before == after and hash(before) == hash(after)
    assert before.read_guard != after.read_guard
