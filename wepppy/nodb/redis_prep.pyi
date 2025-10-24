from __future__ import annotations

from enum import Enum
from typing import Dict, Optional

class TaskEnum(Enum):
    if_exists_rmtree = "rmtree"
    project_init = "project_init"
    set_outlet = "set_outlet"
    abstract_watershed = "abstract_watershed"
    build_channels = "build_channels"
    find_outlet = "find_outlet"
    build_subcatchments = "build_subcatchments"
    build_landuse = "build_landuse"
    build_soils = "build_soils"
    build_climate = "build_climate"
    fetch_rap_ts = "build_rap_ts"
    run_wepp_hillslopes = "run_wepp_hillslopes"
    run_wepp_watershed = "run_wepp_watershed"
    run_observed = "run_observed"
    run_debris = "run_debris"
    run_watar = "run_watar"
    run_rhem = "run_rhem"
    fetch_dem = "fetch_dem"
    landuse_map = "landuse_map"
    init_sbs_map = "init_sbs_map"
    run_omni_scenarios = "run_omni_scenarios"
    run_omni_contrasts = "run_omni_contrasts"
    dss_export = "dss_export"
    set_readonly = "set_readonly"
    run_path_cost_effective = "run_path_ce"

    def label(self) -> str: ...

    def emoji(self) -> str: ...


class RedisPrep:
    wd: str
    cfg_fn: Optional[str]
    run_id: str

    def __init__(self, wd: str, cfg_fn: Optional[str] = ...) -> None: ...

    def __getstate__(self) -> Dict[str, Optional[str]]: ...

    @staticmethod
    def getInstance(
        wd: str = ...,
        allow_nonexistent: bool = ...,
        ignore_lock: bool = ...,
    ) -> "RedisPrep": ...

    @staticmethod
    def tryGetInstance(
        wd: str = ...,
        allow_nonexistent: bool = ...,
        ignore_lock: bool = ...,
    ) -> Optional["RedisPrep"]: ...

    @staticmethod
    def getInstanceFromRunID(
        runid: str,
        allow_nonexistent: bool = ...,
        ignore_lock: bool = ...,
    ) -> "RedisPrep": ...

    @property
    def dump_filepath(self) -> str: ...

    def dump(self) -> None: ...

    def lazy_load(self) -> None: ...

    @property
    def sbs_required(self) -> bool: ...

    @sbs_required.setter
    def sbs_required(self, value: bool) -> None: ...

    @property
    def has_sbs(self) -> bool: ...

    @has_sbs.setter
    def has_sbs(self, value: bool) -> None: ...

    def timestamp(self, key: TaskEnum) -> None: ...

    def timestamps_report(self) -> str: ...

    def remove_timestamp(self, key: TaskEnum) -> None: ...

    def remove_all_timestamp(self) -> None: ...

    def __setitem__(self, key: str, value: int) -> None: ...

    def __getitem__(self, key: str) -> Optional[int]: ...

    def set_rq_job_id(self, key: str, job_id: str) -> None: ...

    def get_rq_job_id(self, key: str) -> Optional[str]: ...

    def get_rq_job_ids(self) -> Dict[str, str]: ...

    def set_archive_job_id(self, job_id: str) -> None: ...

    def get_archive_job_id(self) -> Optional[str]: ...

    def clear_archive_job_id(self) -> None: ...
