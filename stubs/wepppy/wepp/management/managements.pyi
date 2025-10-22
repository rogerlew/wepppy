from __future__ import annotations

from enum import Enum
from typing import Any, Dict, Iterable, List, Optional, Sequence, Set

WEPPPY_MAN_DIR: str


class ScenarioBase:
    root: Any
    def __init__(self) -> None: ...
    def setroot(self, root: Any) -> None: ...


class SectionType(Enum):
    Plant: int
    Op: int
    Ini: int
    Surf: int
    Contour: int
    Drain: int
    Year: int


class ScenarioReference(ScenarioBase):
    section_type: Optional[SectionType]
    loop_name: Optional[str]
    def __init__(
        self,
        section_type: Optional[SectionType] = ...,
        loop_name: Optional[str] = ...,
        root: Any = ...,
        this: Any = ...,
    ) -> None: ...


class PlantLoopCropland(ScenarioBase): ...


class PlantLoopRangeland(ScenarioBase): ...


class PlantLoopForest(ScenarioBase): ...


class PlantLoopRoads(ScenarioBase): ...


class OpLoopCropland(ScenarioBase): ...


class OpLoopRangeland(ScenarioBase): ...


class OpLoopForest(ScenarioBase): ...


class OpLoopRoads(ScenarioBase): ...


class IniLoopCropland(ScenarioBase): ...


class IniLoopRangeland(ScenarioBase): ...


class IniLoopForest(ScenarioBase): ...


class IniLoopRoads(ScenarioBase): ...


class SurfLoopCropland(ScenarioBase): ...


class SurfLoopRangeland(ScenarioBase): ...


class SurfLoopForest(ScenarioBase): ...


class SurfLoopRoads(ScenarioBase): ...


class ContourLoopCropland(ScenarioBase): ...


class DrainLoopCropland(ScenarioBase): ...


class DrainLoopRangeland(ScenarioBase): ...


class DrainLoopRoads(ScenarioBase): ...


class YearLoopCroplandAnnualFallowHerb(ScenarioBase): ...


class YearLoopCroplandAnnualFallowBurn(ScenarioBase): ...


class YearLoopCroplandAnnualFallowSillage(ScenarioBase): ...


class YearLoopCroplandAnnualFallowCut(ScenarioBase): ...


class YearLoopCroplandAnnualFallowRemove(ScenarioBase): ...


class YearLoopCroplandAnnualFallow(ScenarioBase): ...


class YearLoopCroplandPerennialCut(ScenarioBase): ...


class YearLoopCroplandPerennialGraze(ScenarioBase): ...


class YearLoopCroplandPerennial(ScenarioBase): ...


class YearLoopCropland(ScenarioBase): ...


class YearLoopRangelandGrazeLoop(ScenarioBase): ...


class YearLoopRangelandGraze(ScenarioBase): ...


class YearLoopRangelandHerb(ScenarioBase): ...


class YearLoopRangelandBurn(ScenarioBase): ...


class YearLoopRangeland(ScenarioBase): ...


class YearLoopForest(ScenarioBase): ...


class YearLoopRoads(ScenarioBase): ...


class Loop(ScenarioBase):
    name: str
    description: List[str]
    landuse: int


class PlantLoop(Loop): ...


class OpLoop(Loop): ...


class IniLoop(Loop): ...


class SurfLoop(Loop): ...


class ContourLoop(Loop): ...


class DrainLoop(Loop): ...


class YearLoop(Loop): ...


class Loops(List[Any]):
    root: Any


class PlantLoops(Loops): ...


class OpLoops(Loops): ...


class IniLoops(Loops): ...


class SurfLoops(Loops): ...


class ContourLoops(Loops): ...


class DrainLoops(Loops): ...


class YearLoops(Loops): ...


class ManagementLoopManLoop:
    def __init__(self, lines: List[str], root: Any) -> None: ...


class ManagementLoopMan:
    def __init__(self, lines: List[str], parent: Any, root: Any, nyears: int) -> None: ...


class ManagementLoop:
    name: str
    description: List[str]
    nofes: int
    ofeindx: Loops
    loops: Loops
    def __init__(self, lines: List[str], root: Any) -> None: ...


def get_disturbed_classes() -> Set[Optional[str]]: ...


class ManagementSummary:
    key: int
    man_fn: str
    sol_fn: Optional[str]
    man_dir: str
    desc: str
    color: str
    disturbed_class: Optional[str]
    area: Optional[float]
    pct_coverage: Optional[float]
    cancov: float
    inrcov: float
    rilcov: float
    cancov_override: Optional[float]
    inrcov_override: Optional[float]
    rilcov_override: Optional[float]
    def __init__(self, **kwargs: Any) -> None: ...
    @property
    def man_path(self) -> str: ...
    @property
    def sol_path(self) -> Optional[str]: ...
    def get_management(self) -> Management: ...
    def as_dict(self) -> Dict[str, Any]: ...


class Management:
    key: Optional[int]
    man_fn: str
    man_dir: str
    desc: Optional[str]
    color: tuple[int, int, int, int]
    nofe: Optional[int]
    sim_years: int
    plants: PlantLoops
    ops: OpLoops
    inis: IniLoops
    surfs: SurfLoops
    contours: ContourLoops
    drains: DrainLoops
    years: YearLoops
    man: ManagementLoop
    def __init__(self, **kwargs: Any) -> None: ...
    def dump_to_json(self, fn: str) -> None: ...
    @staticmethod
    def load(
        key: Optional[int],
        man_fn: str,
        man_dir: str,
        desc: Optional[str],
        color: Optional[Iterable[int]] = ...,
    ) -> Management: ...
    def setroot(self) -> None: ...
    def set_bdtill(self, value: float) -> None: ...
    def set_cancov(self, value: float) -> None: ...
    def set_rdmax(self, value: float) -> None: ...
    def set_xmxlai(self, value: float) -> None: ...
    def __setitem__(self, attr: str, value: float | int) -> int: ...
    def make_multiple_ofe(self, nofe: int) -> None: ...
    def build_multiple_year_man(self, sim_years: int) -> Management: ...
    def operations_report(self) -> List[Dict[str, Any]]: ...
    def operations_report_cli(self) -> str: ...
    def merge_loops(self, other: Management) -> Management: ...


def merge_managements(mans: Sequence[Management]) -> Management: ...


landuse_management_mapping_options: List[Dict[str, str]]


def load_map(_map: Optional[str] = ...) -> Dict[str, Dict[str, Any]]: ...


class InvalidManagementKey(Exception):
    key: str
    def __init__(self, key: str) -> None: ...


def get_management_summary(dom: int, _map: Optional[str] = ...) -> ManagementSummary: ...


def get_management(dom: int, _map: Optional[str] = ...) -> Management: ...


def get_channel_management() -> Management: ...


def read_management(man_path: str) -> Management: ...


def get_plant_loop_names(runs_dir: str) -> List[str]: ...
