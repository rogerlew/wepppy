from __future__ import annotations

import errno
import os
import shutil

from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait
from pathlib import Path
from typing import Callable, Iterable, Optional

import pyarrow as pa
import pyarrow.parquet as pq

from wepppy.all_your_base import NCPU

INTERCHANGE_TMP_DIR = Path(os.environ.get("WEPP_INTERCHANGE_TMP_DIR", "/dev/shm"))


def _is_writable(path: Path) -> bool:
    return path.is_dir() and os.access(path, os.W_OK | os.X_OK)


def _resolve_tmp_path(target_path: Path, tmp_dir: Optional[Path]) -> Path:
    if tmp_dir is not None and _is_writable(tmp_dir):
        candidate = tmp_dir / f"{target_path.name}.tmp"
        if candidate.exists():
            candidate.unlink()
        return candidate

    fallback_dir = target_path.parent
    fallback_dir.mkdir(parents=True, exist_ok=True)
    fallback_path = fallback_dir / f"{target_path.name}.tmp"
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
    writer: Optional[pq.ParquetWriter] = None
    tmp_persisted = False
    try:
        if not file_list:
            pq.write_table(empty_table, tmp_path)
            tmp_persisted = True
            _commit_tmp(tmp_path, target)
            return target

        pending_tables: dict[int, Optional[pa.Table]] = {}
        next_index = 0
        worker_count = max_workers or NCPU
        with ThreadPoolExecutor(max_workers=worker_count) as executor:
            futures = {executor.submit(parser, path): idx for idx, path in enumerate(file_list)}
            pending_futures = set(futures.keys())
            while pending_futures:
                done, pending_futures = wait(pending_futures, timeout=15, return_when=FIRST_COMPLETED)
                if not done:
                    continue
                for fut in done:
                    idx = futures.pop(fut)
                    try:
                        table = fut.result()
                    except Exception:
                        for remaining in pending_futures:
                            remaining.cancel()
                        raise
                    pending_tables[idx] = table if table.num_rows > 0 else None

                while next_index in pending_tables:
                    table = pending_tables.pop(next_index)
                    if table is not None:
                        if writer is None:
                            writer = pq.ParquetWriter(
                                tmp_path,
                                schema,
                                compression="snappy",
                                use_dictionary=True,
                            )
                        for batch in table.to_batches():
                            writer.write_batch(batch)
                    next_index += 1

        if writer is None:
            pq.write_table(empty_table, tmp_path)
        else:
            writer.close()
            writer = None
        tmp_persisted = True
        _commit_tmp(tmp_path, target)
        return target
    finally:
        if writer is not None:
            writer.close()
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
