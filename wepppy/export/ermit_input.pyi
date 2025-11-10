from __future__ import annotations

from typing import Any, Sequence


HillslopeModel = tuple[Sequence[float], Sequence[float]]


def calc_ERMiT_grads(hillslope_model: HillslopeModel) -> tuple[float, float, float]: ...


def calc_disturbed_grads(hillslope_model: HillslopeModel) -> tuple[float, float, float, float]: ...


def readSlopeFile(fname: str) -> dict[str, float]: ...


def fmt(x: Any) -> Any: ...


def create_ermit_input(wd: str) -> str: ...
