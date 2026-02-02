import pytest

from wepp_runner.wepp_runner import make_watershed_omni_contrasts_run


pytestmark = pytest.mark.unit


def _line_before(lines, needle):
    idx = lines.index(needle)
    if idx == 0:
        raise AssertionError(f"Missing line before {needle}")
    return lines[idx - 1]


def test_make_watershed_omni_contrasts_run_output_options(tmp_path):
    runs_dir = tmp_path / "runs"
    runs_dir.mkdir()

    output_options = {
        "chnwb": True,
        "soil_pw0": False,
        "plot_pw0": True,
        "ebe_pw0": False,
    }

    make_watershed_omni_contrasts_run(3, ["H1"], str(runs_dir), output_options=output_options)

    run_path = runs_dir / "pw0.run"
    lines = [line.strip() for line in run_path.read_text(encoding="ascii").splitlines()]

    assert _line_before(lines, "../output/loss_pw0.txt") == "1"
    assert _line_before(lines, "../output/chnwb.txt") == "Yes"
    assert _line_before(lines, "../output/plot_pw0.txt") == "Yes"

    assert "../output/chnwb.txt" in lines
    assert "../output/plot_pw0.txt" in lines
    assert "../output/soil_pw0.txt" not in lines
    assert "../output/ebe_pw0.txt" not in lines
