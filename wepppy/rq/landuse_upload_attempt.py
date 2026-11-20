"""Immutable source and aligned raster evidence for one uploaded land-use job."""
from contextlib import ExitStack, contextmanager
from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
import shutil
import stat
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from uuid import UUID, uuid4

from wepppy.microservices.upload_boundary import enforce_extension, prepare_filename


UPLOAD_EXTENSIONS = ("tif", "tiff", "img")


@dataclass(frozen=True)
class LanduseUploadAttempt:
    run_root: Path
    runid: str
    job_id: str
    filename: str

    def __post_init__(self):
        if str(UUID(self.job_id)) != self.job_id:
            raise ValueError("Expected a canonical land-use job identifier.")
        if prepare_filename(self.filename, lowercase_by_default=False) != self.filename:
            raise ValueError("Expected a sanitized land-use upload filename.")
        enforce_extension(self.filename, UPLOAD_EXTENSIONS)

    @property
    def directory(self):
        return self.run_root / "landuse_artifacts" / "upload" / "attempts" / self.job_id

    @property
    def raw(self):
        return self.directory / f"source-{self.filename}"

    @property
    def aligned(self):
        return self.directory / "aligned.tif"

    @contextmanager
    def _directory(self, *, create=False):
        directory = os.open(self.run_root.resolve(), os.O_RDONLY | os.O_DIRECTORY)
        try:
            parts = self.directory.relative_to(self.run_root).parts
            for index, name in enumerate(parts):
                if create:
                    try:
                        os.mkdir(name, dir_fd=directory)
                    except FileExistsError:
                        if index == len(parts) - 1:
                            raise
                child = os.open(name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=directory)
                os.close(directory)
                directory = child
            yield directory
        finally:
            os.close(directory)

    def create(self):
        with self._directory(create=True):
            pass

    @staticmethod
    @contextmanager
    def _read(directory, name):
        descriptor = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=directory)
        with os.fdopen(descriptor, "rb") as stream:
            if not stat.S_ISREG(os.fstat(stream.fileno()).st_mode):
                raise ValueError("Expected a regular land-use raster or receipt.")
            yield stream

    def _binding(self):
        return {"runid": self.runid, "job_id": self.job_id, "filename": self.filename}

    def _digests(self, directory):
        digests = {}
        for artifact in (self.raw, self.aligned):
            with self._read(directory, artifact.name) as source:
                digests[artifact.name] = hashlib.file_digest(source, "sha256").hexdigest()
        return digests

    def record(self, inputs):
        temporary = f".build-status-{uuid4().hex}"
        with self._directory() as directory:
            details = {**self._binding(), "digests": self._digests(directory), "inputs": inputs}
            encoded = (json.dumps(details) + "\n").encode()
            try:
                descriptor = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o660, dir_fd=directory)
                with os.fdopen(descriptor, "wb") as stream:
                    stream.write(encoded)
                os.replace(temporary, "build-status.json", src_dir_fd=directory, dst_dir_fd=directory)
            finally:
                try:
                    os.unlink(temporary, dir_fd=directory)
                except FileNotFoundError:
                    pass
            return hashlib.sha256(encoded).hexdigest()

    @contextmanager
    def snapshot(self, receipt_digest, *, applied: Path | None = None):
        with self._directory() as directory, self._read(directory, "build-status.json") as stream:
            encoded = stream.read(65537)
            if len(encoded) > 65536 or hashlib.sha256(encoded).hexdigest() != receipt_digest:
                raise ValueError("The land-use receipt changed after admission.")
            receipt = json.loads(encoded)
            if not isinstance(receipt, dict) or any(receipt.get(key) != value for key, value in self._binding().items()):
                raise ValueError("This land-use upload belongs to a different job.")
            with TemporaryDirectory(prefix="apply-landuse-") as staging, ExitStack() as opened:
                applied_directory = None
                if applied is not None:
                    applied_directory = os.open(applied.resolve(), os.O_RDONLY | os.O_DIRECTORY)
                    opened.callback(os.close, applied_directory)

                for artifact, published_name in ((self.raw, f"_{self.filename}"), (self.aligned, "nlcd.tif")):
                    target = Path(staging) / artifact.name
                    try:
                        source = opened.enter_context(self._read(directory, artifact.name))
                    except FileNotFoundError:
                        if applied_directory is None:
                            raise
                        source = opened.enter_context(self._read(applied_directory, published_name))
                    with target.open("xb") as output:
                        shutil.copyfileobj(source, output)
                    with target.open("rb") as result:
                        digest = hashlib.file_digest(result, "sha256").hexdigest()
                    if digest != receipt["digests"][artifact.name]:
                        raise ValueError("The staged land-use raster changed after validation.")
                yield SimpleNamespace(
                    raw=Path(staging) / self.raw.name,
                    aligned=Path(staging) / self.aligned.name,
                    inputs=receipt["inputs"],
                )

    def remove_completed_rasters(self):
        with self._directory() as directory:
            for artifact in (self.raw, self.aligned):
                try:
                    os.unlink(artifact.name, dir_fd=directory)
                except FileNotFoundError:
                    pass


def apply_landuse_upload(landuse, snapshot, filename, receipt_digest, invalidate_build):
    """Publish the verified input pair and matching NoDb fields under both root leases."""
    from wepppy.nodb.mods.disturbed import Disturbed

    inputs = snapshot.inputs
    destination = landuse.user_defined_raster_destination()

    with TemporaryDirectory(prefix=".publish-landuse-", dir=destination) as staging:
        shutil.copyfile(snapshot.raw, Path(staging) / f"_{filename}")
        shutil.copyfile(snapshot.aligned, Path(staging) / "nlcd.tif")
        landuse.publish_user_defined_raster(
            Path(staging), filename=filename, mapping=inputs["mapping"], dataset=inputs["dataset"],
            buffer_code=inputs["buffer"], expected_inputs=inputs, receipt_digest=receipt_digest,
            invalidate_build=invalidate_build,
        )

    if "disturbed" in landuse.mods:
        Disturbed.getInstance(landuse.wd).apply_build_landuse_updates(
            burn_shrubs=inputs["burn_shrubs"], burn_grass=inputs["burn_grass"],
        )
