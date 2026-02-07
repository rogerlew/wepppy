import logging
import os
import time
from pathlib import Path
from typing import Iterable, Optional

__all__ = [
    'DEFAULT_PERIDOT_INPUT_WAIT_S',
    'DEFAULT_PERIDOT_INPUT_POLL_S',
    'get_peridot_input_wait_s',
    'get_peridot_input_poll_s',
    'wait_for_path',
    'wait_for_paths',
]


DEFAULT_PERIDOT_INPUT_WAIT_S = 60.0
DEFAULT_PERIDOT_INPUT_POLL_S = 0.25


def get_peridot_input_wait_s() -> float:
    raw = os.environ.get('PERIDOT_INPUT_WAIT_S')
    if raw is None:
        return DEFAULT_PERIDOT_INPUT_WAIT_S
    try:
        wait_s = float(raw)
    except ValueError as exc:
        raise ValueError('PERIDOT_INPUT_WAIT_S must be a float') from exc
    if wait_s < 0:
        raise ValueError('PERIDOT_INPUT_WAIT_S must be >= 0')
    return wait_s


def get_peridot_input_poll_s() -> float:
    raw = os.environ.get('PERIDOT_INPUT_POLL_S')
    if raw is None:
        return DEFAULT_PERIDOT_INPUT_POLL_S
    try:
        poll_s = float(raw)
    except ValueError as exc:
        raise ValueError('PERIDOT_INPUT_POLL_S must be a float') from exc
    if poll_s <= 0:
        raise ValueError('PERIDOT_INPUT_POLL_S must be > 0')
    return poll_s


def wait_for_path(
    path: str | Path,
    *,
    timeout_s: Optional[float] = None,
    poll_s: Optional[float] = None,
    require_stable_size: bool = True,
    logger: Optional[logging.Logger] = None,
) -> None:
    if timeout_s is None:
        timeout_s = get_peridot_input_wait_s()
    if poll_s is None:
        poll_s = get_peridot_input_poll_s()

    if isinstance(path, str):
        path = Path(path)

    if path.exists():
        if path.is_dir() or not require_stable_size:
            return
        try:
            size0 = path.stat().st_size
        except FileNotFoundError:
            size0 = None
        if size0 is not None:
            time.sleep(min(poll_s, max(0.0, timeout_s)))
            try:
                size1 = path.stat().st_size
            except FileNotFoundError:
                size1 = None
            if size1 is not None and size1 == size0:
                return

    if timeout_s <= 0:
        raise FileNotFoundError(f'Expected file {path} to exist')

    if logger is not None:
        logger.info('Waiting up to %.2fs for %s', timeout_s, path)

    last_size: Optional[int] = None
    deadline = time.monotonic() + timeout_s
    while True:
        if path.exists():
            if path.is_dir() or not require_stable_size:
                return
            try:
                size = path.stat().st_size
            except FileNotFoundError:
                size = None
            if size is not None:
                if last_size is not None and size == last_size:
                    return
                last_size = size
            else:
                last_size = None
        if time.monotonic() >= deadline:
            raise FileNotFoundError(f'Expected file {path} to be available within {timeout_s:.2f}s')
        time.sleep(poll_s)


def wait_for_paths(
    paths: Iterable[str | Path],
    *,
    timeout_s: Optional[float] = None,
    poll_s: Optional[float] = None,
    require_stable_size: bool = True,
    logger: Optional[logging.Logger] = None,
) -> None:
    for path in paths:
        wait_for_path(
            path,
            timeout_s=timeout_s,
            poll_s=poll_s,
            require_stable_size=require_stable_size,
            logger=logger,
        )
