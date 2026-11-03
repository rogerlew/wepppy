"""Reproducible paired Roads studies using canonical builders and native readers.

The module owns evidence plumbing, not parameter formulas or study selection.
A caller declares cases, provenance and contrasts before invoking execution.
"""
from __future__ import annotations

from dataclasses import replace
import hashlib
import json
import math
from pathlib import Path
import shutil
import subprocess
import time

from tests.roads import roads_matrix as matrix


def digest(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def save_new(path, value):
    with Path(path).open("x") as stream:
        json.dump(value, stream, indent=2, sort_keys=True, allow_nan=False)
        stream.write("\n")


def inventory(root):
    root = Path(root)
    result = {}
    for path in sorted(root.rglob("*")):
        if path.is_symlink():
            raise ValueError(f"Study artifacts must not be symlinks: {path}")
        if path.is_file():
            result[str(path.relative_to(root))] = digest(path)
    return result


def verify(root, bindings):
    root = Path(root).resolve()
    for relative, expected in bindings.items():
        path = root / relative
        if (Path(relative).is_absolute() or ".." in Path(relative).parts
                or path.is_symlink() or not path.resolve().is_relative_to(root)
                or not path.is_file() or digest(path) != expected):
            raise ValueError(f"Study input drift or alias: {relative}")


def signature(record):
    """Scientific input identity, excluding filenames/run decks and case labels."""
    return tuple(record["input_sha256"][f"wepp/roads/runs/p1.{kind}"]
                 for kind in ("slp", "sol", "man", "cli"))


def paired_input_changes(baseline, contrast):
    before, after = baseline["input_sha256"], contrast["input_sha256"]
    if before.keys() != after.keys():
        raise ValueError("Paired input membership differs")
    return sorted(name for name in before if before[name] != after[name])


def interaction(baseline, first, second, combined):
    values = (baseline, first, second, combined)
    if not all(math.isfinite(value) for value in values):
        raise ValueError("Nonfinite interaction response")
    return combined - first - second + baseline


def paired_events(baseline, contrast):
    """Compare native daily export/runoff on the same calendar, including zeros."""
    import duckdb

    with duckdb.connect() as con:
        for name, root in (("baseline", baseline), ("contrast", contrast)):
            path = Path(root) / "wepp/roads/output/interchange/H.pass.parquet"
            con.read_parquet(str(path)).create_view(name)
            if con.execute(f'SELECT count(*) FROM (SELECT year,julian FROM {name} GROUP BY year,julian HAVING count(*) != 1)').fetchone()[0]:
                raise ValueError("Duplicate paired native calendar date")
        for left, right in (("baseline", "contrast"), ("contrast", "baseline")):
            if con.execute(f'SELECT count(*) FROM (SELECT year,julian FROM {left} EXCEPT SELECT year,julian FROM {right})').fetchone()[0]:
                raise ValueError("Paired native calendars differ")
        con.execute('''CREATE TEMP TABLE delta AS SELECT b.year,b.julian,
            c.runvol-b.runvol AS runoff_delta_m3,
            c.runvol*(c.sedcon_1+c.sedcon_2+c.sedcon_3+c.sedcon_4+c.sedcon_5)
            -b.runvol*(b.sedcon_1+b.sedcon_2+b.sedcon_3+b.sedcon_4+b.sedcon_5) AS sediment_delta_kg
            FROM baseline b JOIN contrast c USING(year,julian)''')
        changed = con.execute('SELECT count(*) FROM delta WHERE runoff_delta_m3 != 0 OR sediment_delta_kg != 0').fetchone()[0]
        events = con.execute('SELECT * FROM delta ORDER BY abs(sediment_delta_kg) DESC,year,julian LIMIT 10').fetchall()
        annual = con.execute('SELECT year,sum(runoff_delta_m3),sum(sediment_delta_kg) FROM delta GROUP BY year ORDER BY year').fetchall()
    return dict(changed_days=changed,
                largest_sediment_days=[dict(year=r[0], julian=r[1], runoff_delta_m3=r[2], sediment_delta_kg=r[3]) for r in events],
                annual=[dict(year=r[0], runoff_delta_m3=r[1], sediment_delta_kg=r[2]) for r in annual])


def validate_calendar_context(root, expected_cli_sha256):
    """Reject a reader calendar that differs from the actual native climate."""
    import pyarrow.parquet as pq
    from tests.roads.extract_fixture import climate_dates
    from wepppy.wepp.interchange._rust_interchange import resolve_cli_calendar_path

    root = Path(root)
    output = root / "wepp/roads/output"
    expected = root / "climate"
    selected = next((parent / "climate" for parent in (output, *output.parents)
                     if (parent / "climate").exists()), None)
    if selected != expected or expected.is_symlink():
        raise ValueError("Unexpected ancestor calendar context")
    actual = root / "wepp/roads/runs/p1.cli"
    if digest(actual) != expected_cli_sha256:
        raise ValueError("Native climate differs from prepared receipt")
    source = expected / "site.cli"
    if (list(expected.glob("*.cli")) != [source] or source.is_symlink()
            or digest(source) != digest(actual)):
        raise ValueError("Reader climate differs from native climate")
    cached = expected / "wepp_cli.parquet"
    if cached.is_symlink():
        raise ValueError("Reader calendar cache is aliased")
    resolved = resolve_cli_calendar_path(output)
    if resolved != cached:
        raise ValueError("Reader calendar context is unavailable")
    dates = climate_dates(actual)
    observed = pq.read_table(resolved, columns=["year", "month", "day_of_month"]).to_pylist()
    if [(r["year"], r["month"], r["day_of_month"]) for r in observed] != [(d.year, d.month, d.day) for d in dates]:
        raise ValueError("Cached reader calendar differs from native calendar")
    return dict(native_cli_sha256=digest(actual), reader_cli_sha256=digest(source),
                reader_parquet_sha256=digest(resolved), days=len(dates),
                first=str(dates[0]), last=str(dates[-1]))


def prepare(root, case, *, geometry=None, traffic=None, binary="wepp_261029"):
    """Prepare one profile exclusively; retain actual canonical builder readback."""
    from wepppy.nodb.mods.roads import Roads

    root = Path(root)
    root.mkdir(parents=True, exist_ok=False)
    matrix.initialize(root)
    roads = Roads(str(root), "disturbed9002-wbt-mofe.cfg")
    selected = replace(case, traffic=traffic) if traffic is not None else case
    record = matrix.prepare(roads, root, selected, 1,
                            requested_overrides=geometry, wepp_bin=binary)
    record["binary"] = binary
    binary_path = Path(__file__).resolve().parents[2] / "wepp_runner/bin" / binary
    record["binary_sha256"] = digest(binary_path)
    record["requested_contrast"] = {"geometry": geometry or {}, "traffic": traffic}
    shutil.copyfile(root / "wepp/roads/runs/p1.sol", root / "wepp/roads/runs/reference.sol")
    record["prepared_files"] = inventory(root / "wepp/roads/runs")
    save_new(root / "prepared.json", record)
    return record


def execute(root, record):
    """Run a prepared capsule once; preserve failed native evidence explicitly."""
    root = Path(root)
    runs = root / "wepp/roads/runs"
    verify(runs, record["prepared_files"])
    if inventory(runs) != record["prepared_files"]:
        raise ValueError("Unrecorded native runtime input")
    calendar_context = validate_calendar_context(root, record["prepared_files"]["p1.cli"])
    if (root / "execution-start.json").exists():
        raise ValueError("Study execution already started; use a fresh root")
    prepared = root / ("final-prepared.json" if "generated_source" in record else "prepared.json")
    if json.loads(prepared.read_text()) != json.loads(json.dumps(record)):
        raise ValueError("Prepared receipt metadata differs from execution request")
    save_new(root / "execution-start.json", {"prepared_path": prepared.name, "prepared_sha256": digest(prepared)})
    binary = Path(__file__).resolve().parents[2] / "wepp_runner/bin" / record["binary"]
    if digest(binary) != record["binary_sha256"]:
        raise ValueError("Native binary changed after preparation")
    try:
        started = time.monotonic()
        with (runs / "p1.run").open() as deck, (runs / "stdout").open("x") as stdout, (runs / "stderr").open("x") as stderr:
            completed = subprocess.run([str(binary)], cwd=runs, stdin=deck,
                                       stdout=stdout, stderr=stderr, timeout=300)
        if completed.returncode or "WEPP COMPLETED HILLSLOPE SIMULATION SUCCESSFULLY" not in (runs / "stdout").read_text():
            raise RuntimeError("Native execution did not complete")
        output = root / "wepp/roads/output"
        expected = {f"H1.{kind}.dat" for kind in ("loss", "soil", "pass", "plot", "wat", "element", "ebe")}
        if {p.name for p in output.iterdir()} != expected:
            raise ValueError("Missing or unexpected native outputs")
        result = dict(record, status="completed", elapsed_seconds=time.monotonic()-started,
                      calendar_context=calendar_context,
                      output_sha256={str(p.relative_to(root)): digest(p) for p in output.iterdir()})
        verify(runs, record["prepared_files"])
        if digest(binary) != record["binary_sha256"]:
            raise ValueError("Native binary changed during execution")
        save_new(root / "native-result.json", result)
        return result
    except Exception as exc:
        # Deliberate study boundary: retain process/parser failures and partial
        # artifacts before re-raising. A receipt never converts failure to success.
        save_new(root / "failure.json", {
            "exception": type(exc).__name__, "message": str(exc),
            "artifacts": inventory(root / "wepp/roads"),
        })
        raise


def summarize(root, record, *, start_year, years):
    """Read native tables and the production summary; expose role fluxes unchanged."""
    import duckdb
    import pyarrow.parquet as pq
    from wepppy.wepp.interchange.hill_pass_interchange import run_wepp_hillslope_pass_interchange
    from wepppy.wepp.interchange.hill_wat_interchange import run_wepp_hillslope_wat_interchange
    from wepppy.wepp.interchange.hill_element_interchange import run_wepp_hillslope_element_interchange
    from wepppy.wepp.interchange.hill_ebe_interchange import run_wepp_hillslope_ebe_interchange
    from wepppy.nodb.mods.roads._segment_loss_summary import build_segment_loss_summary

    root = Path(root)
    calendar_context = validate_calendar_context(root, record["prepared_files"]["p1.cli"])
    output = root / "wepp/roads/output"
    run_wepp_hillslope_pass_interchange(output, expected_hillslopes=1)
    run_wepp_hillslope_wat_interchange(output, expected_hillslopes=1)
    run_wepp_hillslope_element_interchange(output, start_year=start_year, expected_hillslopes=1)
    run_wepp_hillslope_ebe_interchange(output, start_year=start_year, expected_hillslopes=1)
    save_new(root / "wepp/roads/segments/roads.segment.pass.manifest.json", [record])
    relative = build_segment_loss_summary(root, output / "interchange",
                                           expected_years=years, start_year=start_year)
    rows = pq.read_table(root / relative).to_pylist()
    if len(rows) != 1:
        raise ValueError("Expected one profile summary")
    summary = rows[0]
    table_root = output / "interchange"
    width = record["emitted"]["width_m"]
    expected_areas = [width * length for length in record["emitted"]["lengths_m"]]
    with duckdb.connect() as con:
        for kind in ("pass", "wat", "element", "ebe"):
            con.read_parquet(str(table_root / f"H.{kind}.parquet")).create_view(kind + "_rows")
        geometry = con.execute('SELECT OFE, min(Area), max(Area) FROM wat_rows GROUP BY OFE ORDER BY OFE').fetchall()
        if len(geometry) != len(expected_areas):
            raise ValueError("Native OFE count differs from prepared slope")
        for (ofe, minimum, maximum), area in zip(geometry, expected_areas, strict=True):
            # Same printed WAT area precision bound as the canonical Roads suite.
            if minimum != maximum or not math.isclose(minimum, area, rel_tol=1e-6, abs_tol=.0051):
                raise ValueError(f"Native/prepared area mismatch at OFE {ofe}")
        annual = con.execute('''SELECT year, sum(runvol) runoff_m3,
            sum(sbrunv) subsurface_m3, sum(gwbfv) groundwater_m3,
            sum(tdet) detachment_kg, sum(tdep) deposition_kg,
            sum(runvol * (sedcon_1+sedcon_2+sedcon_3+sedcon_4+sedcon_5)) export_kg
            FROM pass_rows GROUP BY year ORDER BY year''').fetch_arrow_table()
        pq.write_table(annual, root / "annual.parquet")
        boundary = con.execute('''SELECT OFE, sum(SedLeave) * ? / ? AS boundary_kg_yr,
            min(SedLeave) AS minimum_kg_m, max(SedLeave) AS maximum_kg_m
            FROM element_rows GROUP BY OFE ORDER BY OFE''', [width, years]).fetchall()
        if any(not math.isfinite(v) or v < 0 for row in boundary for v in row[1:]):
            raise ValueError("Invalid native sediment boundary")
    result = dict(summary=summary, native_areas=geometry, calendar_context=calendar_context,
                  role_boundary=[dict(ofe=row[0], role=record["ofe_order"][row[0]-1],
                                      boundary_kg_yr=row[1], minimum_kg_m=row[2], maximum_kg_m=row[3])
                                 for row in boundary],
                  full_water_storage_closure_claim=False,
                  event_tables={str(p.relative_to(root)): digest(p) for p in table_root.glob("H.*.parquet")},
                  annual_sha256=digest(root / "annual.parquet"))
    save_new(root / "response.json", result)
    return result
