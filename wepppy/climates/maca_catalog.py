"""Supported MACAv2-METDATA projections and provider ensemble members."""

MODELS = (
    "bcc-csm1-1", "bcc-csm1-1-m", "BNU-ESM", "CanESM2", "CCSM4", "CNRM-CM5",
    "CSIRO-Mk3-6-0", "GFDL-ESM2G", "GFDL-ESM2M", "HadGEM2-CC365",
    "HadGEM2-ES365", "inmcm4", "IPSL-CM5A-MR", "IPSL-CM5A-LR", "IPSL-CM5B-LR",
    "MIROC5", "MIROC-ESM", "MIROC-ESM-CHEM", "MRI-CGCM3", "NorESM1-M",
)
SCENARIOS = {"RCP4.5": "rcp45_2006_2099", "RCP8.5": "rcp85_2006_2099"}
DEFAULT_PROJECTION = "GFDL-ESM2G/RCP8.5"
PROJECTION_OPTIONS = tuple(
    (f"{model}/{scenario}", f"{model} · {scenario} (2006–2099)")
    for model in MODELS for scenario in SCENARIOS
)


class MacaSelectionError(ValueError):
    """An explicit or saved MACA selection is unsupported."""

    field = "maca_projection"


def ensemble_member(model: str) -> str:
    if not isinstance(model, str) or model not in MODELS:
        raise MacaSelectionError("Select a supported MACA driving model.")
    return "r6i1p1" if model == "CCSM4" else "r1i1p1"


def parse_projection(projection: str) -> tuple[str, str]:
    if not isinstance(projection, str) or projection not in dict(PROJECTION_OPTIONS):
        raise MacaSelectionError("Select a supported MACA driving model and scenario.")
    model, scenario = projection.split("/")
    return model, SCENARIOS[scenario]
