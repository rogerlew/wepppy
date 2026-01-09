from __future__ import annotations

from typing import Any, Dict, Iterable, List, Optional, Tuple

__all__ = ["WatershedFeature", "WatershedCollection"]

def _normalize_geojson_crs_name(name: str) -> str: ...
def _extract_geojson_crs(data: Dict[str, Any]) -> Optional[str]: ...

class WatershedFeature:
    feature: Dict[str, Any]
    id: Any
    properties: Dict[str, Any]
    geometry: Dict[str, Any]
    type: Optional[str]
    coordinates: Any
    crs: Optional[str]
    runid: str
    index: int
    _area_m2: Optional[float]
    bbox: List[float]

    def __init__(
        self,
        feature: Dict[str, Any],
        runid: str,
        *,
        index: int,
        crs: Optional[str] = ...,
    ) -> None: ...
    def save_geojson(self, filepath: str) -> None: ...
    def is_valid(self) -> bool: ...
    def get_padded_bbox(self, pad: float, output_crs: str) -> List[float]: ...
    def build_raster_mask(self, template_filepath: str, dst_filepath: str) -> None: ...
    def contains_point(
        self, point: Tuple[float, float], *, point_crs: Optional[str] = ...
    ) -> bool: ...
    @property
    def area_m2(self) -> float: ...

class WatershedCollection:
    geojson_features: List[Dict[str, Any]]
    data: Dict[str, Any]
    runid_template: Optional[str]

    def __init__(self, geojson_filepath: str) -> None: ...
    def __iter__(self) -> Iterable[WatershedFeature]: ...
    def update_analysis_results(self, metadata: Dict[str, Any]) -> Dict[str, Any]: ...
    @property
    def runid_template_is_valid(self) -> bool: ...
    @classmethod
    def load_from_analysis_results(
        cls,
        analysis_state: Dict[str, Any],
        runid_template_state: Optional[Dict[str, Any]],
    ) -> WatershedCollection: ...
    @property
    def analysis_results(self) -> Dict[str, Any]: ...
    @property
    def checksum(self) -> Optional[str]: ...
    def validate_template(self, template: str, preview_limit: int = ...) -> Dict[str, Any]: ...
    @staticmethod
    def evaluate_template(
        template: str,
        feature_context: Dict[str, Any],
        *,
        allowed_functions: Optional[Dict[str, Any]] = ...,
    ) -> str: ...
    @staticmethod
    def default_template_functions() -> Dict[str, Any]: ...
    def template_feature_context(self, index: int) -> Dict[str, Any]: ...
