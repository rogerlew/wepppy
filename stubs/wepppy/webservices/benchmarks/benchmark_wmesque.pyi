from __future__ import annotations

from typing import List, Tuple


DATASET: str
BBOX: List[float]
CELLSIZE: float


def run_request(endpoint: str, output_dir: str, request_id: int) -> Tuple[bool, float, str]: ...


def main(url: str, total_requests: int, concurrency: int) -> None: ...
