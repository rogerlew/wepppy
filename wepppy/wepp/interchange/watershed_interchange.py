from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from .watershed_chanwb_interchange import run_wepp_watershed_chanwb_interchange
from .watershed_chan_peak_interchange import run_wepp_watershed_chan_peak_interchange
from .watershed_chnwb_interchange import run_wepp_watershed_chnwb_interchange
from .watershed_ebe_interchange import run_wepp_watershed_ebe_interchange
from .watershed_loss_interchange import run_wepp_watershed_loss_interchange
from .watershed_pass_interchange import run_wepp_watershed_pass_interchange
from .watershed_soil_interchange import run_wepp_watershed_soil_interchange


def run_wepp_watershed_interchange(wepp_output_dir: Path | str, *, start_year: int | None = None) -> Path:
    base = Path(wepp_output_dir)
    if not base.exists():
        raise FileNotFoundError(base)

    start_year_kwargs = {"start_year": start_year} if start_year is not None else {}

    tasks = [
        (run_wepp_watershed_pass_interchange, {}),
        (run_wepp_watershed_ebe_interchange, dict(start_year_kwargs)),
        (run_wepp_watershed_chanwb_interchange, dict(start_year_kwargs)),
        (run_wepp_watershed_chan_peak_interchange, dict(start_year_kwargs)),
        (run_wepp_watershed_chnwb_interchange, dict(start_year_kwargs)),
        (run_wepp_watershed_soil_interchange, {}),
        (run_wepp_watershed_loss_interchange, {}),
    ]

    with ThreadPoolExecutor(max_workers=len(tasks)) as executor:
        futures = {executor.submit(func, base, **kwargs): func for func, kwargs in tasks}
        for future in as_completed(futures):
            func = futures[future]
            try:
                future.result()
            except Exception as exc:
                raise RuntimeError(f"Watershed interchange task {func.__name__} failed") from exc

    return base / "interchange"
