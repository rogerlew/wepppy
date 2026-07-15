from __future__ import annotations

import os
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq

from wepppy.nodb.mods.ag_fields import corpus_execution


def test_render_minimal_hillslope_run_is_pass_focused() -> None:
    lines = corpus_execution.render_minimal_hillslope_run(1857, 17).splitlines()

    assert lines[5] == "../output/H1857.pass.dat"
    assert lines[8] == "../output/H1857.loss.dat"
    assert lines[9:19] == ["No"] * 10
    assert lines[19:23] == ["p1857.man", "p1857.slp", "p1857.cli", "p1857.sol"]
    assert lines[-2:] == ["17", "0"]


def test_run_parent_corpus_records_success(
    tmp_path: Path,
    monkeypatch,
) -> None:
    parent_runs = tmp_path / "parent_runs"
    subfield_runs = tmp_path / "subfield_runs"
    parent_runs.mkdir()
    subfield_runs.mkdir()
    for name in corpus_execution.REQUIRED_CONTEXT_FILES:
        (parent_runs / name).write_text(f"context:{name}\n", encoding="utf-8")

    plan_path = tmp_path / "ofe_plan.parquet"
    pq.write_table(
        pa.Table.from_pylist(
            [
                {
                    "parent_wepp_id": 7,
                    "ofe_id": 1,
                    "normalized_start": 0.0,
                    "normalized_end": 1.0,
                    "source_kind": "background",
                    "sub_field_id": None,
                }
            ]
        ),
        plan_path,
    )
    summary_path = tmp_path / "parent_summary.parquet"
    pq.write_table(
        pa.Table.from_pylist(
            [
                {
                    "parent_wepp_id": 7,
                    "residual_width_m": 12.5,
                    "fit_status": "candidate",
                }
            ]
        ),
        summary_path,
    )

    def fake_synthesize(**kwargs):
        parent_wepp_id = kwargs["parent_wepp_id"]
        target_runs_dir = kwargs["target_runs_dir"]
        for suffix in (".man", ".slp", ".cli", ".sol"):
            (target_runs_dir / f"p{parent_wepp_id}{suffix}").write_text(
                f"fixture {suffix}\n", encoding="utf-8"
            )
        return {
            "parent_wepp_id": parent_wepp_id,
            "ofe_count": 1,
            "referenced_yearly_scenario_count": 1,
            "breakpoints": [0.0, 1.0],
            "target_width_m": kwargs["target_width_m"],
            "target_length_m": 10.0,
            "target_area_m2": 125.0,
        }

    monkeypatch.setattr(
        corpus_execution,
        "synthesize_concept1_parent_inputs",
        fake_synthesize,
    )
    fake_binary = tmp_path / "fake_wepp.py"
    fake_binary.write_text(
        r"""#!/usr/bin/env python3
from pathlib import Path
import re
import sys
control = sys.stdin.read()
match = re.search(r"\.\./output/(H[0-9]+\.pass\.dat)", control)
assert match is not None
(Path.cwd().parent / "output" / match.group(1)).write_text("valid pass\n")
print("SIMULATION YEAR = 17")
print("WEPP COMPLETED HILLSLOPE SIMULATION SUCCESSFULLY")
""",
        encoding="utf-8",
    )
    os.chmod(fake_binary, 0o755)

    output_dir = tmp_path / "corpus"
    result = corpus_execution.run_parent_corpus(
        ofe_plan=plan_path,
        parent_summary=summary_path,
        parent_runs=parent_runs,
        subfield_runs=subfield_runs,
        output_dir=output_dir,
        wepp_bin=fake_binary,
        sim_years=17,
        workers=1,
        timeout_seconds=10,
    )

    assert result["parent_count"] == 1
    assert result["passed_count"] == 1
    assert result["failure_count"] == 0
    rows = pq.read_table(output_dir / "execution_results.parquet").to_pylist()
    assert rows[0]["execution_status"] == "passed"
    assert rows[0]["pass_size_bytes"] > 0
    assert rows[0]["last_simulation_year"] == 17


def test_classify_execution_rejects_non_finite_pass(tmp_path: Path) -> None:
    pass_path = tmp_path / "H7.pass.dat"
    pass_path.write_text("1 2 NaN 4\n", encoding="utf-8")

    assert (
        corpus_execution._classify_execution(
            returncode=0,
            timed_out=False,
            stdout=corpus_execution.SUCCESS_MARKER,
            stderr="",
            pass_path=pass_path,
        )
        == "non_finite_pass"
    )


def test_classify_execution_reports_invalid_producer(tmp_path: Path) -> None:
    assert (
        corpus_execution._classify_execution(
            returncode=2,
            timed_out=False,
            stdout="Invalid producer value in management state\n",
            stderr="",
            pass_path=tmp_path / "missing.pass.dat",
        )
        == "invalid_producer"
    )
