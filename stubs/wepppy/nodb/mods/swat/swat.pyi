from __future__ import annotations

from typing import Any, ClassVar, Dict, List, Optional

from wepppy.nodb.base import NoDbBase

__all__: list[str] = ["SwatNoDbLockedException", "Swat"]


class SwatNoDbLockedException(Exception):
    ...


class Swat(NoDbBase):
    filename: ClassVar[str]
    __name__: ClassVar[str]

    enabled: bool
    swatplus_version_major: int
    swatplus_version_minor: int
    swat_bin: str
    template_dir: str
    recall_filename_template: str
    recall_subdir: str
    recall_wst: str
    recall_object_type: str
    include_subsurface: bool
    include_tile: bool
    cli_calendar_path: Optional[str]
    time_start_year: int
    force_time_start_year: bool
    width_method: str
    width_fallback: str
    netw_area_units: str
    disable_aquifer: bool
    qswat_wm: float
    qswat_we: float
    qswat_dm: float
    qswat_de: float
    channel_params: Dict[str, Any]
    recall_manifest: Optional[List[Dict[str, Any]]]
    build_summary: Optional[Dict[str, Any]]
    last_build_at: Optional[str]
    run_summary: Optional[Dict[str, Any]]
    last_run_at: Optional[str]
    status: str
    _recall_calendar_lookup: Optional[Dict[int, List[tuple[int, int]]]]
    _recall_calendar_ready: bool

    def __new__(cls, *args: object, **kwargs: object) -> Swat: ...

    def __init__(
        self,
        wd: str,
        cfg_fn: str,
        run_group: Optional[str] = ...,
        group_name: Optional[str] = ...,
    ) -> None: ...

    @property
    def swat_dir(self) -> str: ...

    @property
    def swat_txtinout_dir(self) -> str: ...

    @property
    def swat_recall_dir(self) -> str: ...

    @property
    def swat_manifests_dir(self) -> str: ...

    @property
    def swat_logs_dir(self) -> str: ...

    @property
    def swat_outputs_dir(self) -> str: ...

    def build_recall_connections(self) -> List[tuple[int, int]]: ...
    def build_inputs(self) -> Dict[str, Any]: ...
    def build_recall(self, recall_connections: List[tuple[int, int]]) -> List[Dict[str, Any]]: ...
    def build_connectivity(self) -> List[Dict[str, Any]]: ...
    def patch_txtinout(
        self,
        recall_manifest: List[Dict[str, Any]],
        channels: List[Dict[str, Any]],
    ) -> Optional[tuple[int, int, int, int]]: ...
    def run_swat(self) -> Dict[str, Any]: ...
    def validate(self, recall_manifest: List[Dict[str, Any]], channels: List[Dict[str, Any]]) -> None: ...
