from __future__ import annotations

from typing import Any, ClassVar, Dict, Optional

from wepppy.nodb.base import NoDbBase
from wepppy.topo.watershed_collection import WatershedFeature

__all__ = ["CulvertsRunner"]


class CulvertsRunner(NoDbBase):
    __name__: ClassVar[str]
    filename: ClassVar[str]
    DEFAULT_RETENTION_DAYS: ClassVar[int]
    DEFAULT_DEM_REL_PATH: ClassVar[str]
    DEFAULT_WATERSHEDS_REL_PATH: ClassVar[str]
    DEFAULT_FLOVEC_REL_PATH: ClassVar[str]
    DEFAULT_FULL_STREAM_REL_PATH: ClassVar[str]
    DEFAULT_STREAMS_CHNJNT_REL_PATH: ClassVar[str]
    DEFAULT_NETFUL_REL_PATH: ClassVar[str]
    DEFAULT_CHNJNT_REL_PATH: ClassVar[str]
    DEFAULT_BASE_DIRNAME: ClassVar[str]
    POINT_ID_FIELD: ClassVar[str]
    def __init__(self, wd: str, cfg_fn: str = "culvert.cfg") -> None: ...
    @property
    def runs_dir(self) -> str: ...
    @property
    def base_wd(self) -> str: ...
    @property
    def base_runid(self) -> Optional[str]: ...
    @property
    def culvert_batch_uuid(self) -> Optional[str]: ...
    @property
    def payload_metadata(self) -> Optional[Dict[str, Any]]: ...
    @property
    def model_parameters(self) -> Optional[Dict[str, Any]]: ...
    @property
    def runs(self) -> Dict[str, Dict[str, Any]]: ...
    @property
    def completed_at(self) -> Optional[str]: ...
    @property
    def retention_days(self) -> Optional[int]: ...
    @property
    def run_config(self) -> str: ...
    @property
    def order_reduction_passes(self) -> int: ...
    @order_reduction_passes.setter
    def order_reduction_passes(self, value: int) -> None: ...
    def create_run_if_missing(
        self,
        run_id: str,
        payload_metadata: Dict[str, Any],
        model_parameters: Optional[Dict[str, Any]] = ...,
    ) -> None: ...
    def load_watershed_features(
        self, watersheds_geojson_path: str
    ) -> Dict[str, WatershedFeature]: ...
