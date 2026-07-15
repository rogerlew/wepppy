from __future__ import annotations

import errno
import os
import shutil

from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
from typing import Callable, Iterable, Optional

import pyarrow as pa
import pyarrow.parquet as pq
from pyarrow import fs
from multiprocessing import get_context, context

from wepppy.all_your_base import NCPU

INTERCHANGE_TMP_DIR = Path(os.environ.get("WEPP_INTERCHANGE_TMP_DIR", "/dev/shm"))
_LOCAL_FILESYSTEM = fs.LocalFileSystem()
_FORCE_SERIAL = os.environ.get("WEPP_INTERCHANGE_FORCE_SERIAL", "").lower() in {"1", "true", "yes"}


def _select_context() -> context.BaseContext:
    for name in ("fork", "spawn"):
        try:
            return get_context(name)
        except ValueError:
            continue
    return get_context()


def _is_writable(path: Path) -> bool:
    return path.is_dir() and os.access(path, os.W_OK | os.X_OK)


def _resolve_tmp_path(target_path: Path, tmp_dir: Optional[Path]) -> Path:
    target_parent = target_path.parent
    target_parent.mkdir(parents=True, exist_ok=True)

    def _same_device(path_a: Path, path_b: Path) -> bool:
        try:
            return os.stat(path_a).st_dev == os.stat(path_b).st_dev
        except OSError:
            return False

    if tmp_dir is not None and _is_writable(tmp_dir) and _same_device(tmp_dir, target_parent):
        candidate = tmp_dir / f"{target_path.name}.tmp"
        if candidate.exists():
            candidate.unlink()
        return candidate

    fallback_path = target_parent / f"{target_path.name}.tmp"
    if fallback_path.exists():
        fallback_path.unlink()
    return fallback_path


def _commit_tmp(tmp_path: Path, target_path: Path) -> None:
    try:
        tmp_path.replace(target_path)
    except OSError as exc:
        if exc.errno == errno.EXDEV:
            shutil.move(str(tmp_path), str(target_path))
        else:
            raise


def _default_empty_table(schema: pa.Schema) -> pa.Table:
    empty_columns = {name: [] for name in schema.names}
    return pa.table(empty_columns, schema=schema)


_TMP_ERROR_ERRNOS = {errno.EACCES, errno.EPERM, errno.EROFS}


def _write_impl(
    file_list: list[Path],
    parser: Callable[[Path], pa.Table],
    schema: pa.Schema,
    target: Path,
    *,
    tmp_dir: Optional[Path],
    max_workers: Optional[int],
    empty_table: pa.Table,
) -> Path:
    tmp_path = _resolve_tmp_path(target, tmp_dir)
    tmp_persisted = False

    def _write_serial() -> None:
        writer: Optional[pq.ParquetWriter] = None
        wrote_any_local = False
        try:
            for path in file_list:
                table = parser(path)
                if table.num_rows == 0:
                    continue
                if writer is None:
                    writer = pq.ParquetWriter(
                        tmp_path,
                        schema,
                        compression="snappy",
                        use_dictionary=True,
                        filesystem=_LOCAL_FILESYSTEM,
                    )
                table = table.combine_chunks()
                writer.write_table(table)
                wrote_any_local = True

            if not wrote_any_local:
                pq.write_table(
                    empty_table,
                    tmp_path,
                    filesystem=_LOCAL_FILESYSTEM,
                    compression="snappy",
                    use_dictionary=True,
                )
        finally:
            if writer is not None:
                writer.close()

    try:
        if not file_list:
            pq.write_table(empty_table, tmp_path, filesystem=_LOCAL_FILESYSTEM, compression="snappy", use_dictionary=True)
            tmp_persisted = True
            _commit_tmp(tmp_path, target)
            return target

        if max_workers == 0:
            _write_serial()
            tmp_persisted = True
            _commit_tmp(tmp_path, target)
            return target

        worker_count = max_workers or NCPU
        mp_context = _select_context()
        writer: Optional[pq.ParquetWriter] = None
        wrote_any = False
        try:
            with ProcessPoolExecutor(max_workers=worker_count, mp_context=mp_context) as executor:
                futures = {}
                next_to_submit = 0
                initial_window = min(worker_count, len(file_list))
                while next_to_submit < initial_window:
                    futures[next_to_submit] = executor.submit(parser, file_list[next_to_submit])
                    next_to_submit += 1

                for expected in range(len(file_list)):
                    future = futures.pop(expected)
                    table = future.result()
                    if table.num_rows > 0:
                        if writer is None:
                            writer = pq.ParquetWriter(
                                tmp_path,
                                schema,
                                compression="snappy",
                                use_dictionary=True,
                                filesystem=_LOCAL_FILESYSTEM,
                            )
                        table = table.combine_chunks()
                        writer.write_table(table)
                        wrote_any = True

                    if next_to_submit < len(file_list):
                        futures[next_to_submit] = executor.submit(parser, file_list[next_to_submit])
                        next_to_submit += 1
        finally:
            if writer is not None:
                writer.close()

        if not wrote_any:
            pq.write_table(
                empty_table,
                tmp_path,
                filesystem=_LOCAL_FILESYSTEM,
                compression="snappy",
                use_dictionary=True,
            )

        tmp_persisted = True
        _commit_tmp(tmp_path, target)
        return target
    finally:
        if not tmp_persisted and tmp_path.exists():
            tmp_path.unlink()


def write_parquet_with_pool(
    files: Iterable[Path],
    parser: Callable[[Path], pa.Table],
    schema: pa.Schema,
    target_path: Path,
    *,
    tmp_dir: Optional[Path] = INTERCHANGE_TMP_DIR,
    max_workers: Optional[int] = None,
    empty_table: Optional[pa.Table] = None,
) -> Path:
    file_list = [Path(p) for p in files]
    target = Path(target_path)
    if empty_table is None:
        empty_table = _default_empty_table(schema)

    if _FORCE_SERIAL and max_workers is None:
        max_workers = 0

    try:
        return _write_impl(
            file_list,
            parser,
            schema,
            target,
            tmp_dir=tmp_dir,
            max_workers=max_workers,
            empty_table=empty_table,
        )
    except OSError as exc:
        if tmp_dir is not None and exc.errno in _TMP_ERROR_ERRNOS:
            return _write_impl(
                file_list,
                parser,
                schema,
                target,
                tmp_dir=None,
                max_workers=max_workers,
                empty_table=empty_table,
            )
        raise
