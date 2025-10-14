from __future__ import annotations

import errno
import os
import shutil

import threading
from concurrent.futures import FIRST_COMPLETED, ProcessPoolExecutor, wait
from pathlib import Path
from typing import Callable, Iterable, Optional

import pyarrow as pa
import pyarrow.parquet as pq
from pyarrow import fs
from multiprocessing import get_context, context

from wepppy.all_your_base import NCPU

INTERCHANGE_TMP_DIR = Path(os.environ.get("WEPP_INTERCHANGE_TMP_DIR", "/dev/shm"))
_LOCAL_FILESYSTEM = fs.LocalFileSystem()
_WRITER_SENTINEL = (-1, None)


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

        worker_count = max_workers or NCPU
        mp_context = _select_context()
        try:
            result_queue = mp_context.SimpleQueue()
        except PermissionError:
            _write_serial()
            tmp_persisted = True
            _commit_tmp(tmp_path, target)
            return target
        writer_state: dict[str, object] = {"exception": None, "wrote_any": False}

        def writer_loop() -> None:
            writer: Optional[pq.ParquetWriter] = None
            pending: dict[int, Optional[pa.Table]] = {}
            expected = 0
            wrote_any_local = False
            try:
                while True:
                    idx, table = result_queue.get()
                    if idx == _WRITER_SENTINEL[0]:
                        while expected in pending:
                            tbl = pending.pop(expected)
                            if tbl is not None:
                                if writer is None:
                                    writer = pq.ParquetWriter(
                                        tmp_path,
                                        schema,
                                        compression="snappy",
                                        use_dictionary=True,
                                        filesystem=_LOCAL_FILESYSTEM,
                                    )
                                tbl = tbl.combine_chunks()
                                writer.write_table(tbl)
                                wrote_any_local = True
                            expected += 1
                        break

                    pending[idx] = table
                    while expected in pending:
                        tbl = pending.pop(expected)
                        if tbl is not None:
                            if writer is None:
                                writer = pq.ParquetWriter(
                                    tmp_path,
                                    schema,
                                    compression="snappy",
                                    use_dictionary=True,
                                    filesystem=_LOCAL_FILESYSTEM,
                                )
                            tbl = tbl.combine_chunks()
                            writer.write_table(tbl)
                            wrote_any_local = True
                        expected += 1

                if not wrote_any_local:
                    pq.write_table(
                        empty_table,
                        tmp_path,
                        filesystem=_LOCAL_FILESYSTEM,
                        compression="snappy",
                        use_dictionary=True,
                    )
                writer_state["wrote_any"] = wrote_any_local
            except Exception as exc:
                writer_state["exception"] = exc
            finally:
                if writer is not None:
                    writer.close()

        writer_thread = threading.Thread(target=writer_loop, daemon=True)
        writer_thread.start()

        try:
            with ProcessPoolExecutor(max_workers=worker_count, mp_context=mp_context) as executor:
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
                            result_queue.put(_WRITER_SENTINEL)
                            writer_thread.join()
                            raise
                        payload = table if table.num_rows > 0 else None
                        result_queue.put((idx, payload))
        finally:
            result_queue.put(_WRITER_SENTINEL)
            writer_thread.join()

        if writer_state["exception"] is not None:
            raise writer_state["exception"]  # pragma: no cover

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
