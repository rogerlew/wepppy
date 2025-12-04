from __future__ import annotations

import logging
from typing import Any, Callable, Optional, ParamSpec, TypeVar

from flask import Request, Response
from redis import ConnectionPool, Redis

P = ParamSpec("P")
ResponseValue = TypeVar("ResponseValue")

logger: logging.Logger
redis_wd_cache_client: Optional[Redis]
redis_wd_cache_pool: Optional[ConnectionPool]
pool_kwargs: dict[str, Any]
REDIS_HOST: str
REDIS_WD_CACHE_DB: int


def _playback_path(env_var: str, subdir: str) -> str: ...


def get_wd(runid: str, *, prefer_active: bool = ...) -> str: ...


def get_primary_wd(runid: str) -> str: ...


def get_batch_wd(batch_name: str) -> str: ...


def get_batch_base_wd(batch_name: str) -> str: ...


def get_batch_root_dir() -> str: ...


def get_batch_run_wd(batch_name: str, runid: str) -> str: ...


def url_for_run(endpoint: str, **values: Any) -> str: ...


def error_factory(msg: str = ...) -> Response: ...


def exception_factory(
    msg: BaseException | str = ...,
    stacktrace: str | None = ...,
    runid: str | None = ...,
) -> Response: ...


def success_factory(kwds: Optional[dict[str, Any]] = ...) -> Response: ...


def authorize(runid: str, config: str, require_owner: bool = ...) -> None: ...


def get_run_owners_lazy(runid: str) -> Any: ...


def get_user_models() -> tuple[Any, Any, Any]: ...


def authorize_and_handle_with_exception_factory(
    func: Callable[..., ResponseValue],
) -> Callable[..., Response | ResponseValue]: ...


def handle_with_exception_factory(
    func: Callable[P, ResponseValue],
) -> Callable[P, Response | ResponseValue]: ...


def parse_rec_intervals(request: Request, years: int) -> list[int]: ...
