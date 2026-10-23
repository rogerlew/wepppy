"""Site-derived experiments using the production Roads input builders."""
from dataclasses import asdict, dataclass, replace
from itertools import product
import json
from pathlib import Path
import shutil
import shlex
import math

from tests.roads.extract_fixture import DATA, digest


@dataclass(frozen=True)
class Case:
    geometry: str
    texture: str
    surface: str
    traffic: str
    arrangement: str
    control: str = "core"

    @property
    def name(self):
        return "-".join(asdict(self).values())


ARRANGEMENTS = {
    "bare_direct": ("inslope_bd", (1,)),
    "rocked_direct": ("inslope_rd", (1,)),
    "bare_buffer": ("inslope_bd", (1, 3)),
    "rocked_buffer": ("inslope_rd", (1, 3)),
    "rutted": ("outslope_rutted", (1, 2, 3)),
    "unrutted_three": ("outslope_unrutted", (3, 1, 2)),
    "unrutted_four": ("outslope_unrutted", (3, 1, 2, 3)),
}
CONTROLS = {
    "width_2": ("width_m", 2), "width_8": ("width_m", 8),
    "grade_half": ("grade_factor", .5), "grade_double": ("grade_factor", 2),
    "fill_length_10": ("fill_length_m", 10), "fill_length_60": ("fill_length_m", 60),
    "fill_grade_2": ("fill_slope_pct", 2), "fill_grade_30": ("fill_slope_pct", 30),
    "buffer_length_5": ("buffer_length_m", 5), "buffer_length_60": ("buffer_length_m", 60),
    "rock_0": ("rfg_pct", 0), "rock_40": ("rfg_pct", 40),
}
REFERENCE = Case("median", "loam", "gravel", "low", "rutted")
CASES = tuple(Case(*values) for values in product(
    ("short", "median", "long"), ("clay", "loam", "sand", "silt"),
    ("gravel", "paved"), ("high", "low", "none"), ARRANGEMENTS
)) + tuple(replace(REFERENCE, control=name) for name in CONTROLS)


def site():
    return json.loads((DATA / "site.json").read_text())


def execution_identity():
    from tests.roads.roads_analysis import source_hashes
    from wepppyo3 import wepp_interchange

    sources = source_hashes()
    selected = {k:v for k,v in sources.items() if not k.startswith("tests/roads/") or
                k.startswith("tests/roads/data/") or Path(k).name in
                ("roads_matrix.py", "extract_fixture.py", "test_roads_matrix.py")}
    native = {p.name:digest(p) for p in Path(wepp_interchange.__file__).parent.glob("*.so")}
    if not native:
        raise ValueError("Native extension identity missing")
    return dict(source_sha256=selected, native_sha256=native)


def initialize(root):
    for relative in ("wepp/roads/runs", "wepp/roads/output", "wepp/roads/segments", "climate"):
        (root / relative).mkdir(parents=True, exist_ok=True)
    for path in (DATA / "shared").iterdir():
        shutil.copy2(path, root / "wepp/roads/runs" / path.name)
    shutil.copy2(DATA / "site.cli", root / "climate/site.cli")
    staged = [root / "climate/site.cli", *(root / "wepp/roads/runs" / p.name for p in (DATA / "shared").iterdir())]
    (root / "staged-inputs.json").write_text(json.dumps({str(p.relative_to(root)):digest(p) for p in staged}, indent=2))
    (root / "execution-identity.json").write_text(json.dumps(execution_identity(), indent=2))


def read_management(path, template, order):
    """Read the legacy template sections and every emitted scenario assignment.

    These legacy files have description formatting unsupported by Management.load;
    retain exact section data and use native WEPP execution as the grammar check.
    """
    import re
    import hashlib

    actual, source = path.read_text(), template.read_text()
    def count(text, marker):
        return int(next(line.split()[0] for line in text.splitlines() if marker in line))
    def sections(text, kind, following):
        start = text.index(f"# looper; number of {kind} scenarios")
        end = text.index("# Management Section #" if following == "Management" else f"# looper; number of {following} scenarios", start)
        block = text[start:end]
        chunks = re.split(r"#\s*" + re.escape(kind) + r" scenario \d+ of \d+", block)[1:]
        result = []
        for chunk in chunks:
            lines = [line.split("#",1)[0].strip() for line in chunk.splitlines()]
            # The following section count precedes its marker at end of block.
            result.append([line for line in lines if line])
        if following != "Management":
            result[-1] = result[-1][:-1]
        return result
    assert count(actual, "# number of OFEs") == count(actual, "# `nofe'") == len(order)
    assert count(actual, "# looper; number of Plant scenarios") == 3
    plants = sections(actual, "Plant", "Operation")
    assert plants == sections(source, "Plant", "Operation") and len(plants) == 3
    selected = order if order in ((1,), (1,3)) else (1,2,3)
    for kind, following in (("Initial Conditions", "Surface Effects"), ("Yearly", "Management")):
        original = sections(source, kind, following)
        assert sections(actual, kind, following) == [original[i-1] for i in selected]
        assert count(actual, f"# looper; number of {kind} scenarios") == len(selected)
    assignments = list(range(1,len(order)+1)) if order in ((1,), (1,3)) else list(order)
    def indices(text, marker):
        return [int(line.split()[0]) for line in text.splitlines() if marker in line]
    assert indices(actual, "# `Initial Conditions indx'") == assignments
    scheduled = indices(actual, "# `YEAR indx'")
    years = len(indices(source, "# `YEAR indx'")) // 3
    assert scheduled == assignments * years
    ofe_positions = [int(v) for v in re.findall(r"# `nycrop'.*OFE : (\d+)", actual)]
    assert ofe_positions == list(range(1,len(order)+1)) * years
    return dict(plant_names=[p[0] for p in plants],
        initial_residue_indices=indices(actual, "# `iresd'"),
        yearly_plant_indices=indices(actual, "# `itype'"),
        ofe_initial_indices=assignments, schedule_years=years,
        schedule_sha256=hashlib.sha256(json.dumps(scheduled).encode()).hexdigest())


def prepare(roads, root: Path, case: Case, identifier: int):
    """Return requested and emitted evidence; no controller defaults are changed."""
    from wepp_runner import make_hillslope_run
    from wepppy.wepp.soils.utils import WeppSoilUtil

    fixture = site()
    source = fixture["geometry"][case.geometry]
    requested = dict(width_m=4., road_length_m=source["segment_length_m"],
        road_slope_pct=source["slope_pct_clamped"], fill_length_m=30., fill_slope_pct=10.,
        buffer_length_m=30., buffer_slope_pct=10., rfg_pct=15.)
    if case.control != "core":
        key, value = CONTROLS[case.control]
        if key == "grade_factor":
            requested["road_slope_pct"] *= value
        else:
            requested[key] = value
    geometry = {k: v for k, v in requested.items() if k != "rfg_pct"}
    geometry["road_slope_pct"] = roads._clamp_percent_slope(geometry["road_slope_pct"])
    effective_grade = geometry["road_slope_pct"]
    clipping = dict(road_grade=effective_grade != requested["road_slope_pct"], unrutted_length=False, unrutted_width=False)
    design, order = ARRANGEMENTS[case.arrangement]
    parity = None
    if design == "outslope_unrutted":
        parity = roads._apply_outslope_unrutted_geometry_parity(
            road_length_m=geometry["road_length_m"], road_width_m=geometry["width_m"],
            road_slope_pct=geometry["road_slope_pct"])
        clipping.update(unrutted_length=not math.isclose(parity["sim_length_m"], geometry["road_length_m"] * parity["geometry_scale"]),
                        unrutted_width=not math.isclose(parity["sim_width_m"], geometry["width_m"] / parity["geometry_scale"]))
        geometry.update(width_m=parity["sim_width_m"], road_length_m=parity["sim_length_m"],
                        road_slope_pct=parity["road_slope_pct"])
    runs = root / "wepp/roads/runs"
    stem = runs / f"p{identifier}"
    slope = stem.with_suffix(".slp")
    if order == (1,):
        roads._write_single_ofe_slope_file(slope, width_m=geometry["width_m"],
            length_m=geometry["road_length_m"], slope_pct=geometry["road_slope_pct"])
    elif order == (1, 3):
        roads._write_routed_two_ofe_slope_file(slope, **{k:v for k,v in geometry.items() if not k.startswith("fill_")})
    elif order == (1, 2, 3):
        roads._write_routed_three_ofe_slope_file(slope, **geometry)
    else:
        args = {k:v for k,v in geometry.items() if not k.startswith("buffer_")}
        args.update(top_landuse_length_m=30., top_landuse_slope_pct=10.)
        if len(order) == 3:
            roads._write_routed_three_ofe_landuse_road_fill_slope_file(slope, **args)
        else:
            roads._write_routed_four_ofe_landuse_road_fill_hill_slope_file(slope, **args,
                bottom_landuse_length_m=geometry["buffer_length_m"], bottom_landuse_slope_pct=geometry["buffer_slope_pct"])
    # Production unrutted uses the rutted soil lookup, including paved tau=1.
    soil = roads._resolve_legacy_soil_template_path(design="outslope_rutted" if design == "outslope_unrutted" else design,
        surface=case.surface, soil_texture=case.texture)
    management = roads._resolve_legacy_management_template_path(traffic=case.traffic)
    soil_args = dict(template_path=soil, output_path=stem.with_suffix(".sol"),
                     traffic=case.traffic, surface=case.surface, rfg_pct=requested["rfg_pct"])
    man_args = dict(template_path=management, output_path=stem.with_suffix(".man"))
    if order == (1,):
        roads._build_single_ofe_soil_file(**soil_args)
        roads._build_single_ofe_management_file(**man_args)
    elif order == (1, 3):
        roads._build_routed_two_ofe_soil_file(**soil_args)
        roads._build_routed_two_ofe_management_file(**man_args)
    elif order == (1, 2, 3):
        roads._build_routed_three_ofe_soil_file(**soil_args)
        shutil.copy2(management, man_args["output_path"])
    else:
        roads._build_routed_mofe_soil_file(**soil_args, ofe_order=order)
        roads._build_routed_mofe_management_file(**man_args, ofe_order=order)
    management_readback = read_management(stem.with_suffix(".man"), management, order)
    parsed_soil = WeppSoilUtil(str(stem.with_suffix(".sol"))).obj["ofes"]
    assert len(parsed_soil) == len(order)
    expected_rocks = {1: 95. if case.surface == "paved" else 65.,
                      2: (requested["rfg_pct"] + 65.) / 2., 3: requested["rfg_pct"]}
    original_road = shlex.split(next(line for line in soil.read_text().splitlines() if line.startswith("'Road'")))
    for ofe, original_index in zip(parsed_soil, order):
        assert ofe["texid"] == original_road[1]
        assert ofe["horizons"][0]["rfg"] == expected_rocks[original_index]
        if original_index == 1:
            divisor = 1 if case.traffic == "high" else 4
            assert math.isclose(ofe["ki"], float(original_road[5]) / divisor)
            assert math.isclose(ofe["kr"], float(original_road[6]) / divisor)
    shutil.copy2(DATA / "site.cli", stem.with_suffix(".cli"))
    make_hillslope_run(identifier, fixture["simulation_years"], str(runs), reveg=False, wepp_bin=fixture["binary"])
    lines = slope.read_text().splitlines()
    emitted = dict(width_m=float(lines[2].split()[1]),
        lengths_m=[float(lines[3 + 2*i].split()[1]) for i in range(int(lines[1]))],
        slope_lines=[lines[4 + 2*i] for i in range(int(lines[1]))])
    assert len(emitted["lengths_m"]) == len(order)
    assert min(emitted["lengths_m"]) > 0 and emitted["width_m"] > 0
    return dict(case=asdict(case), name=case.name, segment_run_id=identifier,
        segment_id=case.name, status="prepared", design=design, surface=case.surface,
        traffic=case.traffic, soil_texture=case.texture, rfg_pct=requested["rfg_pct"],
        requested=requested, parity=parity, emitted=emitted, ofe_order=order,
        effective_geometry=geometry, clipping=clipping, management_readback=management_readback,
        road_width_m=requested["width_m"], segment_length_m=requested["road_length_m"], slope_pct_clamped=effective_grade,
        soil_readback=parsed_soil,
        template_sha256={str(p.relative_to(Path(__file__).parents[2])):digest(p) for p in (soil,management)},
        input_sha256={str(p.relative_to(root)):digest(p) for p in runs.glob(f"p{identifier}.*")})


def execute(root, record):
    from wepp_runner import run_hillslope
    identifier = record["segment_run_id"]
    success, returned, elapsed = run_hillslope(identifier, str(root / "wepp/roads/runs"), wepp_bin=site()["binary"])
    assert success and returned == identifier
    outputs = list((root / "wepp/roads/output").glob(f"H{identifier}.*"))
    for suffix in ("pass.dat", "wat.dat"):
        assert (root / f"wepp/roads/output/H{identifier}.{suffix}").stat().st_size > 0
    record.update(status="completed", elapsed_seconds=elapsed,
        output_sha256={str(p.relative_to(root)):digest(p) for p in outputs})
    (root / f"case-{identifier}.json").write_text(json.dumps(record, indent=2) + "\n")
    return record
