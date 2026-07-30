from pathlib import Path
from typing import Mapping, Sequence

MAX_SAMPLE_ROWS: int
SCENARIO_PRODUCTS: Sequence[tuple[str, str]]
CONTRAST_PRODUCTS: Sequence[tuple[str, str]]
OUTLET_METRIC_DESCRIPTIONS: Mapping[str, str]
COMMON_COLUMN_DESCRIPTIONS: Mapping[str, str]

def generate_omni_scenarios_documentation(
    omni_dir: Path | str,
    to_readme_md: bool = ...,
) -> str: ...
def generate_omni_contrasts_documentation(
    omni_dir: Path | str,
    to_readme_md: bool = ...,
) -> str: ...
