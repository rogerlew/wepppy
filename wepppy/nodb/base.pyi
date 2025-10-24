from __future__ import annotations

import logging
from collections import defaultdict
from concurrent.futures import ProcessPoolExecutor
from configparser import RawConfigParser
from enum import Enum, IntEnum
from pathlib import Path
from typing import Any, Callable, ClassVar, Concatenate, Generator, Iterator, Optional, ParamSpec, TypeVar

import redis

__all__ = [
    "NoDbAlreadyLockedError",
    "redis_nodb_cache_client",
    "redis_status_client",
    "redis_log_level_client",
    "REDIS_HOST",
    "REDIS_PORT",
    "REDIS_NODB_CACHE_DB",
    "REDIS_STATUS_DB",
    "REDIS_LOCK_DB",
    "REDIS_NODB_EXPIRY",
    "REDIS_LOG_LEVEL_DB",
    "LogLevel",
    "try_redis_get_log_level",
    "try_redis_set_log_level",
    "createProcessPoolExecutor",
    "get_config_dir",
    "CaseSensitiveRawConfigParser",
    "get_configs",
    "get_legacy_configs",
    "nodb_setter",
    "nodb_timed",
    "TriggerEvents",
    "NoDbBase",
    "iter_nodb_mods_subclasses",
    "clear_locks",
    "lock_statuses",
    "clear_nodb_file_cache",
]


class NoDbAlreadyLockedError(Exception):
    ...


redis_nodb_cache_client: Optional[redis.StrictRedis]
redis_status_client: Optional[redis.StrictRedis]
redis_log_level_client: Optional[redis.StrictRedis]
REDIS_HOST: str
REDIS_PORT: int
REDIS_NODB_CACHE_DB: int
REDIS_STATUS_DB: int
REDIS_LOCK_DB: int
REDIS_NODB_EXPIRY: int
REDIS_LOG_LEVEL_DB: int


class LogLevel(IntEnum):
    DEBUG: int
    INFO: int
    WARNING: int
    ERROR: int
    CRITICAL: int

    @staticmethod
    def parse(x: str) -> LogLevel: ...

    def __str__(self) -> str: ...


def try_redis_get_log_level(runid: str, default: int | LogLevel = ...) -> int: ...


def try_redis_set_log_level(runid: str, level: str | LogLevel) -> None: ...


def createProcessPoolExecutor(
    max_workers: int,
    logger: Optional[logging.Logger] = ...,
    prefer_spawn: bool = ...,
) -> ProcessPoolExecutor: ...


def get_config_dir() -> str: ...


class CaseSensitiveRawConfigParser(RawConfigParser):
    def optionxform(self, optionstr: str) -> str: ...


def get_configs() -> list[str]: ...


def get_legacy_configs() -> list[str]: ...


P = ParamSpec("P")
R = TypeVar("R")


def nodb_setter(
    setter_func: Callable[Concatenate["NoDbBase", P], R]
) -> Callable[Concatenate["NoDbBase", P], R]: ...


def nodb_timed(
    method_func: Callable[Concatenate["NoDbBase", P], R]
) -> Callable[Concatenate["NoDbBase", P], R]: ...


class TriggerEvents(Enum):
    ON_INIT_FINISH: int
    LANDUSE_DOMLC_COMPLETE: int
    LANDUSE_BUILD_COMPLETE: int
    SOILS_BUILD_COMPLETE: int
    PREPPING_PHOSPHORUS: int
    WATERSHED_ABSTRACTION_COMPLETE: int
    CLIMATE_BUILD_COMPLETE: int
    WEPP_PREP_WATERSHED_COMPLETE: int
    FORK_COMPLETE: int


class NoDbBase(object):
    DEBUG: ClassVar[int]
    _js_decode_replacements: ClassVar[tuple[tuple[str, str], ...]]
    filename: ClassVar[Optional[str]]
    _legacy_module_redirects: ClassVar[dict[str, str]]

    def __init__(
        self,
        wd: str,
        cfg_fn: str,
        run_group: Optional[str] = ...,
        group_name: Optional[str] = ...,
    ) -> None: ...

    @property
    def _nodb(self) -> str: ...

    @property
    def _rel_nodb(self) -> str: ...

    @property
    def _file_lock_key(self) -> str: ...

    @property
    def _distributed_lock_key(self) -> str: ...

    @property
    def parent_wd(self) -> Optional[str]: ...

    @parent_wd.setter
    def parent_wd(self, value: str) -> None: ...

    @property
    def is_child_run(self) -> bool: ...

    @property
    def pup_relpath(self) -> Optional[str]: ...

    @property
    def is_omni_run(self) -> bool: ...

    @property
    def _relpath_to_parent(self) -> str: ...

    @property
    def _logger_base_name(self) -> str: ...

    @property
    def class_name(self) -> str: ...

    @property
    def _status_channel(self) -> str: ...

    def _init_logging(self) -> None: ...

    def __getstate__(self) -> dict[str, Any]: ...

    def timed(self, task_name: str, level: int = ...) -> Generator[None, None, None]: ...

    @classmethod
    def getInstance(
        cls,
        wd: str = ...,
        allow_nonexistent: bool = ...,
        ignore_lock: bool = ...,
    ) -> "NoDbBase": ...

    @classmethod
    def tryGetInstance(
        cls,
        wd: str = ...,
        allow_nonexistent: bool = ...,
        ignore_lock: bool = ...,
    ) -> Optional["NoDbBase"]: ...

    @classmethod
    def getInstanceFromRunID(
        cls,
        runid: str,
        allow_nonexistent: bool = ...,
        ignore_lock: bool = ...,
    ) -> "NoDbBase": ...

    def locked(self, validate_on_success: bool = ...) -> Generator[None, None, None]: ...

    def dump_and_unlock(self, validate: bool = ...) -> None: ...

    @classmethod
    def _post_dump_and_unlock(cls, instance: "NoDbBase") -> "NoDbBase": ...

    def dump(self) -> None: ...

    @classmethod
    def _get_nodb_path(cls, wd: str) -> str: ...

    @classmethod
    def _preprocess_json_for_decode(cls, json_text: str) -> str: ...

    @classmethod
    def _decode_jsonpickle(cls, json_text: str) -> Any: ...

    @classmethod
    def _ensure_legacy_module_imports(cls, json_text: str) -> None: ...

    @classmethod
    def _import_mod_module(cls, mod_name: str) -> None: ...

    @classmethod
    def _post_instance_loaded(cls, instance: Any) -> Any: ...

    @property
    def watershed_instance(self) -> Any: ...

    @property
    def wepp_instance(self) -> Any: ...

    @property
    def climate_instance(self) -> Any: ...

    @property
    def soils_instance(self) -> Any: ...

    @property
    def landuse_instance(self) -> Any: ...

    @property
    def ron_instance(self) -> Any: ...

    @property
    def redis_prep_instance(self) -> Any: ...

    @property
    def disturbed_instance(self) -> Any: ...

    @property
    def has_sbs(self) -> bool: ...

    @property
    def config_stem(self) -> str: ...

    def config_get_bool(self, section: str, option: str, default: Optional[bool] = ...) -> Optional[bool]: ...

    def config_get_float(self, section: str, option: str, default: Optional[float] = ...) -> Optional[float]: ...

    def config_get_int(self, section: str, option: str, default: Optional[int] = ...) -> Optional[int]: ...

    def config_iter_section(self, section: str) -> Iterator[tuple[str, Optional[str]]]: ...

    def config_get_str(self, section: str, option: str, default: Optional[str] = ...) -> Optional[str]: ...

    def config_get_path(self, section: str, option: str, default: Optional[str] = ...) -> Optional[str]: ...

    def config_get_raw(self, section: str, option: str, default: Any = ...) -> Any: ...

    def config_get_list(self, section: str, option: str, default: Any = ...) -> Any: ...

    def set_attrs(self, attrs: Any) -> None: ...

    @property
    def locales(self) -> tuple[str, ...]: ...

    @property
    def stub(self) -> dict[str, Any]: ...

    def islocked(self) -> bool: ...

    def lock(self, ttl: Optional[int] = ...) -> None: ...

    def unlock(self, flag: Optional[str] = ...) -> None: ...

    @property
    def run_group(self) -> Optional[str]: ...

    @run_group.setter
    def run_group(self, value: str) -> None: ...

    @property
    def group_name(self) -> Optional[str]: ...

    @group_name.setter
    def group_name(self, value: str) -> None: ...

    @property
    def runid(self) -> str: ...

    @property
    def multi_ofe(self) -> bool: ...

    @property
    def readonly(self) -> bool: ...

    @readonly.setter
    def readonly(self, value: bool) -> None: ...

    @staticmethod
    def ispublic(wd: str) -> bool: ...

    @property
    def public(self) -> bool: ...

    @public.setter
    def public(self, value: bool) -> None: ...

    @property
    def DEBUG(self) -> bool: ...

    @DEBUG.setter
    def DEBUG(self, value: bool) -> None: ...

    @property
    def VERBOSE(self) -> bool: ...

    @VERBOSE.setter
    def VERBOSE(self, value: bool) -> None: ...

    @property
    def _configparser(self) -> RawConfigParser: ...

    def _load_mods(self) -> None: ...

    def trigger(self, evt: TriggerEvents) -> None: ...

    @property
    def mods(self) -> Any: ...

    @property
    def dem_dir(self) -> str: ...

    @property
    def dem_fn(self) -> str: ...

    @property
    def topaz_wd(self) -> str: ...

    @property
    def taudem_wd(self) -> str: ...

    @property
    def wbt_wd(self) -> str: ...

    @property
    def wat_dir(self) -> str: ...

    @property
    def wat_js(self) -> str: ...

    @property
    def lc_dir(self) -> str: ...

    @property
    def lc_fn(self) -> str: ...

    @property
    def domlc_fn(self) -> str: ...

    @property
    def soils_dir(self) -> str: ...

    @property
    def ssurgo_fn(self) -> str: ...

    @property
    def domsoil_fn(self) -> str: ...

    @property
    def cli_dir(self) -> str: ...

    @property
    def wepp_dir(self) -> str: ...

    @property
    def runs_dir(self) -> str: ...

    @property
    def output_dir(self) -> str: ...

    @property
    def wepp_interchange_dir(self) -> str: ...

    @property
    def fp_runs_dir(self) -> str: ...

    @property
    def fp_output_dir(self) -> str: ...

    @property
    def plot_dir(self) -> str: ...

    @property
    def stats_dir(self) -> str: ...

    @property
    def export_dir(self) -> str: ...

    @property
    def export_winwepp_dir(self) -> str: ...

    @property
    def export_arc_dir(self) -> str: ...

    @property
    def export_legacy_arc_dir(self) -> str: ...

    @property
    def observed_dir(self) -> str: ...

    @property
    def observed_fn(self) -> str: ...

    @property
    def ash_dir(self) -> str: ...

    @property
    def wmesque_version(self) -> int: ...

    @property
    def wmesque_endpoint(self) -> Optional[str]: ...


def iter_nodb_mods_subclasses() -> Iterator[tuple[str, type[NoDbBase]]]: ...


def clear_locks(runid: str, pup_relpath: Optional[str] = ...) -> list[str]: ...


def lock_statuses(runid: str) -> defaultdict[str, bool]: ...


def clear_nodb_file_cache(runid: str, pup_relpath: Optional[str] = ...) -> list[Path]: ...
