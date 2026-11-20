"""Run-owned staged input and receipt for a Climate upload job."""

from contextlib import contextmanager
from dataclasses import dataclass
import hashlib
import json
import os
import re
import shutil
import stat
from pathlib import Path
from tempfile import TemporaryDirectory
from uuid import UUID, uuid4

from wepppy.microservices.upload_boundary import enforce_extension, prepare_filename


def validate_cli_basename(filename: str) -> str:
    """Require the exact sanitized filename used by the submission endpoint."""
    if prepare_filename(filename, lowercase_by_default=False) != filename:
        raise ValueError("Expected a sanitized climate upload filename")
    enforce_extension(filename, ("cli",))
    return filename


@dataclass(frozen=True)
class ClimateUploadAttempt:
    run_root: Path
    runid: str
    job_id: str
    filename: str

    def __post_init__(self) -> None:
        if str(UUID(self.job_id)) != self.job_id:
            raise ValueError("Expected a canonical climate upload job identifier")
        validate_cli_basename(self.filename)

    @property
    def directory(self) -> Path:
        return self.run_root / "climate_artifacts" / "climate_upload" / "attempts" / self.job_id

    @property
    def source(self) -> Path:
        return self.directory / self.filename

    @property
    def receipt(self) -> Path:
        return self.directory / "build-status.json"

    @contextmanager
    def _open_directory(self, *, create: bool = False):
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

    def create(self) -> None:
        with self._open_directory(create=True):
            pass

    def _binding(self) -> dict[str, str]:
        return {"runid": self.runid, "job_id": self.job_id, "filename": self.filename}

    @staticmethod
    @contextmanager
    def _open_regular(directory: int, name: str):
        descriptor = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=directory)
        with os.fdopen(descriptor, "rb") as stream:
            if not stat.S_ISREG(os.fstat(stream.fileno()).st_mode):
                raise ValueError("Expected a regular climate upload file.")
            yield stream

    def source_digest(self) -> str:
        with self._open_directory() as directory, self._open_regular(directory, self.filename) as stream:
            return hashlib.file_digest(stream, "sha256").hexdigest()

    def read_receipt(self) -> dict:
        with self._open_directory() as directory, self._open_regular(directory, self.receipt.name) as stream:
            receipt = json.load(stream)
        if not isinstance(receipt, dict) or any(receipt.get(key) != value for key, value in self._binding().items()):
            raise ValueError("The climate upload receipt belongs to a different job.")
        digest = receipt.get("sha256")
        build_job_id = receipt.get("build_job_id")
        if (receipt.get("state") not in ("staged", "failed", "applied")
                or not isinstance(digest, str) or re.fullmatch(r"[0-9a-f]{64}", digest) is None
                or "build_job_id" not in receipt
                or (build_job_id is not None and not isinstance(build_job_id, str))):
            raise ValueError("The climate upload receipt contains invalid metadata.")
        return receipt

    @contextmanager
    def snapshot(self, digest: str):
        """Read, check and pin the exact bytes the worker will validate and apply."""
        with TemporaryDirectory(prefix="wepp-climate-upload-") as tempdir:
            candidate = Path(tempdir) / self.filename
            with self._open_directory() as directory, self._open_regular(directory, self.filename) as source:
                with candidate.open("xb") as target:
                    shutil.copyfileobj(source, target)
            with candidate.open("rb") as target:
                if hashlib.file_digest(target, "sha256").hexdigest() != digest:
                    raise ValueError("The staged climate upload changed after submission.")
            yield candidate

    def remove_consumed_source(self, digest: str) -> None:
        with self._open_directory() as directory, self._open_regular(directory, self.filename) as stream:
            if hashlib.file_digest(stream, "sha256").hexdigest() != digest:
                raise ValueError("The staged climate upload changed after application.")
            source = os.stat(self.filename, dir_fd=directory, follow_symlinks=False)
            if not os.path.samestat(source, os.fstat(stream.fileno())):
                raise ValueError("The staged climate upload file was replaced after application.")
            os.unlink(self.filename, dir_fd=directory)

    def record(self, state: str, digest: str, build_job_id: str | None) -> None:
        details = {**self._binding(), "state": state, "sha256": digest, "build_job_id": build_job_id}
        temporary = f".upload-status-{uuid4().hex}"
        with self._open_directory() as directory:
            try:
                fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o666, dir_fd=directory)
                with os.fdopen(fd, "w") as stream:
                    json.dump(details, stream, sort_keys=True)
                    stream.write("\n")
                os.replace(temporary, self.receipt.name, src_dir_fd=directory, dst_dir_fd=directory)
            finally:
                try:
                    os.unlink(temporary, dir_fd=directory)
                except FileNotFoundError:
                    pass
