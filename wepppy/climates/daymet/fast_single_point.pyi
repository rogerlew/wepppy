from __future__ import annotations

import numpy as np
import pandas as pd


daymet_proj4: str


def single_point_extraction(
    lon: float,
    lat: float,
    start_year: int,
    end_year: int,
) -> pd.DataFrame: ...


def extract_variable(
    x: float,
    y: float,
    dataset: str,
    start_year: int,
    end_year: int,
) -> np.ndarray: ...
