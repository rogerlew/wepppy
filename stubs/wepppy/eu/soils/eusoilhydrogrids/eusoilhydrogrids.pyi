from __future__ import annotations


class SoilHydroGrids:
    datasets: tuple[str, ...]
    depths: tuple[str, ...]
    depth_offsets_mm: tuple[int, ...]

    def __init__(self) -> None: ...

    def query(self, lng: float, lat: float, dataset: str) -> dict[str, tuple[int, float | None]]: ...

    @staticmethod
    def get_fn(dataset: str, depth: str) -> str: ...
