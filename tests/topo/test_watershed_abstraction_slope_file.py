from __future__ import annotations

import importlib
import os
from pathlib import Path

import numpy as np
import pytest

from wepppy.topo.watershed_abstraction.slope_file import (
    SlopeFile,
    clip_slope_file_length,
    mofe_distance_fractions,
)


pytestmark = pytest.mark.unit
slope_file_module = importlib.import_module("wepppy.topo.watershed_abstraction.slope_file")


def _write_single_ofe_slope(
    path: Path,
    *,
    version: str = "97.5",
    aspect: float = 311.995,
    width: float = 82.4,
    length: float = 100.0,
    points: list[tuple[float, float]] | None = None,
    z0: float | None = None,
) -> None:
    if points is None:
        points = [
            (0.0, 0.9),
            (0.25, 0.8),
            (0.5, 0.6),
            (0.75, 0.5),
            (1.0, 0.4),
        ]

    npts = len(points)
    header = [version, "1"]
    if version.startswith("2023"):
        assert z0 is not None
        header.append(f"{aspect} {width} {z0}")
    else:
        header.append(f"{aspect} {width}")
    header.append(f"{npts} {length}")
    row = " ".join(f"{d:.5f}, {s:.4f}" for d, s in points)
    path.write_text("\n".join(header + [row]) + "\n", encoding="utf-8")


def _parse_mofe_slope_profiles(path: Path) -> list[list[tuple[float, float]]]:
    lines = [line.strip() for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    n_ofes = int(lines[1])
    cursor = 3
    ofe_profiles: list[list[tuple[float, float]]] = []

    for _ in range(n_ofes):
        npts = int(lines[cursor].split()[0])
        cursor += 1

        row = lines[cursor].replace(",", "").split()
        cursor += 1
        assert len(row) == npts * 2

        profile = [
            (float(row[i * 2]), float(row[i * 2 + 1]))
            for i in range(npts)
        ]
        ofe_profiles.append(profile)

    return ofe_profiles


def test_clip_slope_file_length_clips_length_and_preserves_area(tmp_path: Path) -> None:
    src = tmp_path / "src.slp"
    dst = tmp_path / "dst.slp"
    _write_single_ofe_slope(src, width=80.0, length=100.0)

    clip_slope_file_length(str(src), str(dst), clip_length=40.0)

    lines = [line.strip() for line in dst.read_text(encoding="utf-8").splitlines() if line.strip()]
    width = float(lines[2].split()[1])
    length = float(lines[3].split()[1])
    assert length == 40.0
    assert width == 200.0
    assert width * length == 8000.0


def test_clip_slope_file_length_noop_when_shorter_than_clip(tmp_path: Path) -> None:
    src = tmp_path / "src.slp"
    dst = tmp_path / "dst.slp"
    _write_single_ofe_slope(src, width=70.0, length=50.0)

    clip_slope_file_length(str(src), str(dst), clip_length=120.0)

    lines = [line.strip() for line in dst.read_text(encoding="utf-8").splitlines() if line.strip()]
    width = float(lines[2].split()[1])
    length = float(lines[3].split()[1])
    assert width == 70.0
    assert length == 50.0


def test_clip_slope_file_length_caps_each_mofe_and_preserves_total_area(tmp_path: Path) -> None:
    src = tmp_path / "src.mofe.slp"
    dst = tmp_path / "dst.mofe.slp"
    src.write_text(
        "\n".join(
            [
                "97.5",
                "3",
                "311.995 80.0",
                "2 40",
                "0.0000, 0.9000 1.0000, 0.8000",
                "2 90",
                "0.0000, 0.8000 1.0000, 0.6000",
                "2 120",
                "0.0000, 0.6000 1.0000, 0.4000",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    clip_slope_file_length(str(src), str(dst), clip_length=60.0)

    lines = dst.read_text(encoding="utf-8").splitlines()
    assert [float(lines[index].split()[1]) for index in (3, 5, 7)] == [40.0, 60.0, 60.0]
    assert float(lines[2].split()[1]) == pytest.approx(125.0)
    assert float(lines[2].split()[1]) * 160.0 == pytest.approx(80.0 * 250.0)
    assert [lines[index] for index in (0, 1, 4, 6, 8)] == [
        "97.5",
        "3",
        "0.0000, 0.9000 1.0000, 0.8000",
        "0.0000, 0.8000 1.0000, 0.6000",
        "0.0000, 0.6000 1.0000, 0.4000",
    ]


@pytest.mark.parametrize(
    ("lengths", "expected"),
    [([20.0, 40.0], [20.0, 40.0]), ([60.0, 90.0], [60.0, 60.0])],
)
def test_clip_slope_file_length_handles_all_short_and_exact_limit_ofes(
    tmp_path: Path,
    lengths: list[float],
    expected: list[float],
) -> None:
    src = tmp_path / "src.mofe.slp"
    dst = tmp_path / "dst.mofe.slp"
    src.write_text(
        "97.5\n2\n311.995 80.0\n"
        f"2 {lengths[0]}\n0, 0.9 1, 0.8\n"
        f"2 {lengths[1]}\n0, 0.8 1, 0.6\n",
        encoding="utf-8",
    )

    clip_slope_file_length(str(src), str(dst), 60.0)

    lines = dst.read_text(encoding="utf-8").splitlines()
    assert [float(lines[index].split()[1]) for index in (3, 5)] == expected
    assert float(lines[2].split()[1]) * sum(expected) == pytest.approx(80.0 * sum(lengths))


def test_clip_slope_file_length_preserves_2023_header_and_z0(tmp_path: Path) -> None:
    src = tmp_path / "src.slp"
    dst = tmp_path / "dst.slp"
    _write_single_ofe_slope(src, version="2023.3", z0=1163.4, width=80.0, length=90.0)

    clip_slope_file_length(str(src), str(dst), 60.0)

    lines = dst.read_text(encoding="utf-8").splitlines()
    assert lines[0] == "2023.3"
    assert lines[2].split()[0] == "311.995"
    assert lines[2].split()[2] == "1163.4"


@pytest.mark.parametrize("clip_length", [0.0, -1.0, float("nan"), float("inf")])
def test_clip_slope_file_length_rejects_invalid_limit_without_replacing_destination(
    tmp_path: Path,
    clip_length: float,
) -> None:
    src = tmp_path / "src.slp"
    dst = tmp_path / "dst.slp"
    _write_single_ofe_slope(src)
    dst.write_text("prior destination\n", encoding="utf-8")

    with pytest.raises(ValueError, match="finite and greater than zero"):
        clip_slope_file_length(str(src), str(dst), clip_length)

    assert dst.read_text(encoding="utf-8") == "prior destination\n"


def test_clip_slope_file_length_malformed_source_preserves_destination(tmp_path: Path) -> None:
    src = tmp_path / "src.slp"
    dst = tmp_path / "dst.slp"
    src.write_text("97.5\n2\n311.995 80\n2 100\n0, 0.1 1, 0.2\n", encoding="utf-8")
    dst.write_text("prior destination\n", encoding="utf-8")

    with pytest.raises(ValueError, match="Malformed slope file"):
        clip_slope_file_length(str(src), str(dst), 60.0)

    assert dst.read_text(encoding="utf-8") == "prior destination\n"
    assert not list(tmp_path.glob(".dst.slp.*.tmp"))


@pytest.mark.parametrize(
    "source",
    [
        "bogus\n1\n311.995 80\n2 100\n0, 0.1 1, 0.2\n",
        "97.5\n1\nbogus 80\n2 100\n0, 0.1 1, 0.2\n",
        "2023.3\n1\n311.995 80\n2 100\n0, 0.1 1, 0.2\n",
        "97.5\n1\n311.995 80\n3 100\n0, 0.1 0.8, 0.2 0.7, 0.3\n",
        "97.5\n1\n311.995 80\n2 100\n0, 0.1 1, 0.2\ntrailing\n",
    ],
)
def test_clip_slope_file_length_rejects_malformed_complete_source(
    tmp_path: Path,
    source: str,
) -> None:
    src = tmp_path / "src.slp"
    dst = tmp_path / "dst.slp"
    src.write_text(source, encoding="utf-8")
    dst.write_text("prior destination\n", encoding="utf-8")

    with pytest.raises(ValueError, match="Malformed slope file"):
        clip_slope_file_length(str(src), str(dst), 60.0)

    assert dst.read_text(encoding="utf-8") == "prior destination\n"
    assert not list(tmp_path.glob(".dst.slp.*.tmp"))


def test_clip_slope_file_length_replace_failure_preserves_destination_and_cleans_temp(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    src = tmp_path / "src.slp"
    dst = tmp_path / "dst.slp"
    _write_single_ofe_slope(src)
    dst.write_text("prior destination\n", encoding="utf-8")

    def _fail_replace(_src: str, _dst: str) -> None:
        raise OSError("injected replace failure")

    monkeypatch.setattr(slope_file_module.os, "replace", _fail_replace)

    with pytest.raises(OSError, match="injected replace failure"):
        clip_slope_file_length(str(src), str(dst), 60.0)

    assert dst.read_text(encoding="utf-8") == "prior destination\n"
    assert not list(tmp_path.glob(".dst.slp.*.tmp"))


def test_clip_slope_file_length_temp_finalize_failure_preserves_destination_and_cleans_temp(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    src = tmp_path / "src.slp"
    dst = tmp_path / "dst.slp"
    _write_single_ofe_slope(src)
    dst.write_text("prior destination\n", encoding="utf-8")

    def _fail_fsync(_fd: int) -> None:
        raise OSError("injected temp finalize failure")

    monkeypatch.setattr(slope_file_module.os, "fsync", _fail_fsync)

    with pytest.raises(OSError, match="injected temp finalize failure"):
        clip_slope_file_length(str(src), str(dst), 60.0)

    assert dst.read_text(encoding="utf-8") == "prior destination\n"
    assert not list(tmp_path.glob(".dst.slp.*.tmp"))


def test_clip_slope_file_length_rejects_overflowed_width_before_publication(tmp_path: Path) -> None:
    src = tmp_path / "src.slp"
    dst = tmp_path / "dst.slp"
    _write_single_ofe_slope(src, width=1e308, length=1e308)
    dst.write_text("prior destination\n", encoding="utf-8")

    with pytest.raises(ValueError, match="clipped width must be finite"):
        clip_slope_file_length(str(src), str(dst), 60.0)

    assert dst.read_text(encoding="utf-8") == "prior destination\n"
    assert not list(tmp_path.glob(".dst.slp.*.tmp"))


def test_clip_slope_file_length_replaces_hardlink_without_mutating_source(tmp_path: Path) -> None:
    src = tmp_path / "src.slp"
    dst = tmp_path / "dst.slp"
    _write_single_ofe_slope(src, width=80.0, length=100.0)
    original = src.read_text(encoding="utf-8")
    dst.hardlink_to(src)
    assert src.stat().st_ino == dst.stat().st_ino

    clip_slope_file_length(str(src), str(dst), 40.0)

    assert src.read_text(encoding="utf-8") == original
    assert src.stat().st_ino != dst.stat().st_ino
    assert float(dst.read_text(encoding="utf-8").splitlines()[3].split()[1]) == 40.0


def test_clip_slope_file_length_preserves_source_mode(tmp_path: Path) -> None:
    src = tmp_path / "src.slp"
    dst = tmp_path / "dst.slp"
    _write_single_ofe_slope(src)
    src.chmod(0o664)

    clip_slope_file_length(str(src), str(dst), 60.0)

    assert os.stat(dst).st_mode & 0o777 == 0o664


def test_mofe_distance_fractions_returns_cumulative_normalized_lengths(tmp_path: Path) -> None:
    src = tmp_path / "hill_11.mofe.slp"
    src.write_text(
        "\n".join(
            [
                "97.5",
                "3",
                "311.995 82.4",
                "2 10",
                "0.0000, 0.9000 1.0000, 0.8000",
                "2 30",
                "0.0000, 0.8000 1.0000, 0.6000",
                "2 60",
                "0.0000, 0.6000 1.0000, 0.4000",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    fractions = mofe_distance_fractions(str(src))
    assert np.allclose(fractions, np.array([0.0, 0.1, 0.4, 1.0]))


def test_slope_file_2023_header_uses_embedded_z0(tmp_path: Path) -> None:
    src = tmp_path / "hill_13.slp"
    _write_single_ofe_slope(
        src,
        version="2023.1",
        z0=1234.0,
        length=100.0,
        points=[
            (0.0, 0.5),
            (0.5, 0.2),
            (1.0, 0.1),
        ],
    )

    slope = SlopeFile(str(src))
    assert slope.relative_elevs[0] == 1234.0
    assert slope.relative_elevs[1] == 1259.0


def test_segmented_multiple_ofe_drops_duplicate_rounded_distances(tmp_path: Path) -> None:
    src = tmp_path / "hill_11.slp"
    dst = tmp_path / "hill_11.mofe.slp"
    src.write_text(
        "\n".join(
            [
                "97.5",
                "1",
                "311.995 82.4",
                "6 100.0",
                "0.0000, 0.9000 0.2500, 0.8000 0.25001, 0.1000 0.5000, 0.6000 0.7500, 0.5000 1.0000, 0.4000",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    slope = SlopeFile(str(src))
    n_mofes = slope.segmented_multiple_ofe(dst_fn=str(dst), target_length=25, apply_buffer=False)

    assert n_mofes == 4
    ofe_profiles = _parse_mofe_slope_profiles(dst)
    assert len(ofe_profiles) == 4

    for profile in ofe_profiles:
        distances = [distance for distance, _slope in profile]
        assert distances[0] == 0.0
        assert distances[-1] == 1.0
        assert all(curr > prev for prev, curr in zip(distances, distances[1:]))

    second_ofe = ofe_profiles[1]
    assert second_ofe[0] == (0.0, 0.1)


def test_segmented_multiple_ofe_uses_rounded_tail_point_without_appending_duplicate_endpoint(tmp_path: Path) -> None:
    src = tmp_path / "hill_14.slp"
    dst = tmp_path / "hill_14.mofe.slp"
    _write_single_ofe_slope(
        src,
        points=[
            (0.0, 0.9),
            (0.25, 0.8),
            (0.49999, 0.1),
            (0.5, 0.7),
            (0.75, 0.5),
            (1.0, 0.4),
        ],
    )

    slope = SlopeFile(str(src))
    n_mofes = slope.segmented_multiple_ofe(dst_fn=str(dst), target_length=25, apply_buffer=False)
    assert n_mofes == 4

    ofe_profiles = _parse_mofe_slope_profiles(dst)
    second_ofe = ofe_profiles[1]
    assert second_ofe == [(0.0, 0.8), (1.0, 0.1)]


def test_segmented_multiple_ofe_with_buffer_keeps_monotonic_distances(tmp_path: Path) -> None:
    src = tmp_path / "hill_12.slp"
    dst = tmp_path / "hill_12.mofe.slp"
    src.write_text(
        "\n".join(
            [
                "97.5",
                "1",
                "311.995 82.4",
                "6 100.0",
                "0.0000, 0.9000 0.1500, 0.8000 0.15001, 0.2000 0.5000, 0.6000 0.7500, 0.5000 1.0000, 0.4000",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    slope = SlopeFile(str(src))
    n_mofes = slope.segmented_multiple_ofe(
        dst_fn=str(dst),
        target_length=25,
        apply_buffer=True,
        buffer_length=15,
    )

    assert n_mofes >= 2
    ofe_profiles = _parse_mofe_slope_profiles(dst)
    assert len(ofe_profiles) == n_mofes

    for profile in ofe_profiles:
        distances = [distance for distance, _slope in profile]
        assert distances[0] == 0.0
        assert distances[-1] == 1.0
        assert all(curr > prev for prev, curr in zip(distances, distances[1:]))


def test_segmented_multiple_ofe_respects_max_ofes_cap(tmp_path: Path) -> None:
    src = tmp_path / "hill_15.slp"
    dst = tmp_path / "hill_15.mofe.slp"
    _write_single_ofe_slope(src, length=1000.0)

    slope = SlopeFile(str(src))
    n_mofes = slope.segmented_multiple_ofe(dst_fn=str(dst), target_length=50, apply_buffer=False, max_ofes=3)
    assert n_mofes == 3

    lines = [line.strip() for line in dst.read_text(encoding="utf-8").splitlines() if line.strip()]
    assert int(lines[1]) == 3


def test_segmented_multiple_ofe_promotes_zero_rounding_case_to_one_ofe(tmp_path: Path) -> None:
    src = tmp_path / "hill_16.slp"
    dst = tmp_path / "hill_16.mofe.slp"
    _write_single_ofe_slope(src, length=10.0)

    slope = SlopeFile(str(src))
    n_mofes = slope.segmented_multiple_ofe(dst_fn=str(dst), target_length=50, apply_buffer=False)
    assert n_mofes == 1

    lines = [line.strip() for line in dst.read_text(encoding="utf-8").splitlines() if line.strip()]
    assert int(lines[1]) == 1


def test_segmented_multiple_ofe_at_breakpoints_preserves_requested_geometry(tmp_path: Path) -> None:
    src = tmp_path / "hill_18.slp"
    dst = tmp_path / "hill_18.mofe.slp"
    _write_single_ofe_slope(src, width=80.0, length=100.0)

    slope = SlopeFile(str(src))
    n_mofes = slope.segmented_multiple_ofe_at_breakpoints(
        [0.0, 0.2, 0.55, 1.0],
        dst_fn=str(dst),
        target_width=37.5,
    )

    assert n_mofes == 3
    lines = [line.strip() for line in dst.read_text(encoding="utf-8").splitlines() if line.strip()]
    assert int(lines[1]) == 3
    assert float(lines[2].split()[1]) == 37.5
    assert np.allclose(mofe_distance_fractions(str(dst)), [0.0, 0.2, 0.55, 1.0])


@pytest.mark.parametrize(
    "breakpoints",
    [
        [0.1, 1.0],
        [0.0, 0.5, 0.5, 1.0],
        [0.0, float("nan"), 1.0],
    ],
)
def test_segmented_multiple_ofe_at_breakpoints_rejects_invalid_boundaries(
    tmp_path: Path,
    breakpoints: list[float],
) -> None:
    src = tmp_path / "hill_19.slp"
    _write_single_ofe_slope(src)

    slope = SlopeFile(str(src))
    with pytest.raises(ValueError):
        slope.segmented_multiple_ofe_at_breakpoints(breakpoints)


@pytest.mark.parametrize(
    ("apply_buffer", "target_length", "buffer_length", "max_ofes"),
    [
        (False, 25.0, 15.0, 19),
        (True, 25.0, 15.0, 3),
    ],
)
def test_segmented_multiple_ofe_wepppyo3_matches_legacy_python_output(
    tmp_path: Path,
    apply_buffer: bool,
    target_length: float,
    buffer_length: float,
    max_ofes: int,
) -> None:
    src = tmp_path / "hill_17.slp"
    rust_dst = tmp_path / "hill_17.rust.mofe.slp"
    legacy_dst = tmp_path / "hill_17.legacy.mofe.slp"
    _write_single_ofe_slope(
        src,
        length=120.0,
        points=[
            (0.0, 0.9),
            (0.125, 0.8),
            (0.25001, 0.1),
            (0.5, 0.6),
            (0.75001, 0.5),
            (1.0, 0.4),
        ],
    )

    slope = SlopeFile(str(src))
    n_rust = slope.segmented_multiple_ofe(
        dst_fn=str(rust_dst),
        target_length=target_length,
        apply_buffer=apply_buffer,
        buffer_length=buffer_length,
        max_ofes=max_ofes,
    )
    with pytest.warns(DeprecationWarning):
        n_legacy = slope.segmented_multiple_ofe_legacy(
            dst_fn=str(legacy_dst),
            target_length=target_length,
            apply_buffer=apply_buffer,
            buffer_length=buffer_length,
            max_ofes=max_ofes,
        )

    assert n_rust == n_legacy
    assert rust_dst.read_text(encoding="utf-8") == legacy_dst.read_text(encoding="utf-8")
