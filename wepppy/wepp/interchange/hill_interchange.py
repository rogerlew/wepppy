from pathlib import Path
from .hill_ebe_interchange import run_wepp_hillslope_ebe_interchange
from .hill_element_interchange import run_wepp_hillslope_element_interchange
from .hil_loss_interchange import run_wepp_hillslope_loss_interchange
from .hill_pass_interchange import run_wepp_hillslope_pass_interchange
from .hill_soil_interchange import run_wepp_hillslope_soil_interchange
from .hill_wat_interchange import run_wepp_hillslope_wat_interchange

def run_wepp_hillslope_interchange(wepp_output_dir: Path | str) -> Path:
    base = Path(wepp_output_dir)
    if not base.exists():
        raise FileNotFoundError(base)

    run_wepp_hillslope_pass_interchange(base)
    run_wepp_hillslope_ebe_interchange(base)
    run_wepp_hillslope_element_interchange(base)
    run_wepp_hillslope_loss_interchange(base)
    run_wepp_hillslope_soil_interchange(base)
    run_wepp_hillslope_wat_interchange(base)
