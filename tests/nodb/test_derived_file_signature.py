"""Required main-file transaction signatures use real bytes and filesystem guards."""
import errno
import hashlib
import os
from pathlib import Path

import pytest
from wepppy.nodb._derived_build import file_signature

pytestmark = pytest.mark.unit


def test_byte_and_transaction_metadata_semantics(tmp_path):
    source = tmp_path / 'source'
    source.write_bytes(b'AAAA')
    original = source.stat()
    first = file_signature(source)
    os.link(source, tmp_path / 'alias')
    assert file_signature(source) == first
    source.chmod(0o600)
    assert file_signature(source) == first
    replacement = tmp_path / 'replacement'
    replacement.write_bytes(b'AAAA')
    os.utime(replacement, ns=(original.st_atime_ns, original.st_mtime_ns))
    os.replace(replacement, source)
    assert file_signature(source) == first
    source.write_bytes(b'BBBB')
    os.utime(source, ns=(original.st_atime_ns, original.st_mtime_ns))
    changed = file_signature(source)
    assert changed[:3] == first[:3] and changed[3] != first[3]
    os.utime(source, ns=(original.st_atime_ns, original.st_mtime_ns + 1_000_000_000))
    assert file_signature(source) != changed


def test_missing_empty_and_nonregular(tmp_path):
    source = tmp_path / 'source'
    with pytest.raises(FileNotFoundError):
        file_signature(source)
    source.touch()
    assert file_signature(source)[3] == hashlib.sha256(b'').hexdigest()
    assert file_signature(tmp_path)[3] is None
    fifo = tmp_path / "fifo"
    os.mkfifo(fifo)
    with pytest.raises(OSError) as caught:
        file_signature(fifo)
    assert caught.value.errno == errno.EINVAL


@pytest.mark.parametrize('mutation', ['grow', 'replace', 'mtime', 'truncate', 'read_error'])
def test_read_drift_rejects_without_unbounded_consumption(tmp_path, monkeypatch, mutation):
    source = tmp_path / 'source'
    source.write_bytes(b'AAAA')
    replacement = tmp_path / 'replacement'
    replacement.write_bytes(b'BBBB')
    real_open = Path.open
    reads = []
    read_error = PermissionError(errno.EACCES, 'injected read denial', str(source))
    class ChangingReader:
        def __init__(self, stream):
            self.stream = stream
        def __enter__(self):
            return self
        def __exit__(self, *args):
            self.stream.close()
        def fileno(self):
            return self.stream.fileno()
        def read(self, count):
            reads.append(count)
            if mutation == 'read_error':
                raise read_error
            content = self.stream.read(count)
            if len(reads) == 1:
                if mutation == 'grow':
                    with real_open(source, 'ab') as writer:
                        writer.write(b'GROWTH')
                elif mutation == 'truncate':
                    with real_open(source, 'wb') as writer:
                        writer.write(b'A')
                elif mutation == 'replace':
                    os.replace(replacement, source)
                else:
                    version = source.stat()
                    os.utime(source, ns=(version.st_atime_ns, version.st_mtime_ns + 1_000_000_000))
            return content
    monkeypatch.setattr(Path, 'open', lambda path, *args, **kwargs: ChangingReader(real_open(path, *args, **kwargs)))
    with pytest.raises(OSError) as caught:
        file_signature(source)
    if mutation == 'read_error':
        assert caught.value is read_error
        assert reads == [5]
    else:
        assert caught.value.errno == errno.ESTALE
        assert caught.value.filename == str(source)
        assert reads == [5, 1]


def test_native_directory_backed_raster_remains_readable(tmp_path):
    from osgeo import gdal
    from wepppyo3.raster_characteristics import identify_median_single_raster_key

    keys = tmp_path / 'keys.tif'
    raster = tmp_path / 'source.zarr'
    for path, driver, value in [(keys, 'GTiff', 1), (raster, 'Zarr', 25)]:
        dataset = gdal.GetDriverByName(driver).Create(str(path), 2, 2, 1, gdal.GDT_Byte)
        dataset.SetGeoTransform((0, 1, 0, 2, 0, -1))
        dataset.GetRasterBand(1).Fill(value)
        dataset = None
    assert raster.is_dir()
    version = raster.stat()
    assert file_signature(raster) == (str(raster.resolve()), version.st_mtime_ns, version.st_size, None)
    assert identify_median_single_raster_key(key_fn=str(keys), parameter_fn=str(raster), band_indx=1) == {'1': 25.0}
