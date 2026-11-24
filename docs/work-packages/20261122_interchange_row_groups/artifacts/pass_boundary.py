"""Exercise the native PASS entry point with distinct one-day source identities."""
from pathlib import Path
from tempfile import TemporaryDirectory

import pyarrow.parquet as pq
from wepppyo3.wepp_interchange import hillslope_pass_files_to_parquet


def main():
    count = 47_582
    with TemporaryDirectory() as directory:
        root = Path(directory)
        fixture = root / "sample"
        fixture.write_text("WEPP PASS\nsimulation start year 2000\nh3\nh4\nh5\nNO EVENT2000 1 1.25 2.50\n")
        paths = []
        for hill in range(1, count + 1):
            path = root / f"H{hill}.pass.dat"
            path.symlink_to(fixture)
            paths.append(str(path))
        output = root / "H.pass.parquet"
        summary = hillslope_pass_files_to_parquet(
            paths, str(output), 1, 0, pass_family="legacy_ascii"
        )
        artifact = pq.ParquetFile(output)
        assert artifact.metadata.num_rows == summary["rows_written"] == count
        assert artifact.metadata.num_row_groups == summary["row_groups"] < 32_768
        assert artifact.read(columns=["wepp_id"])[0].to_pylist() == list(range(1, count + 1))
        print(f"{count} ordered IDs, {artifact.metadata.num_row_groups} physical groups")


if __name__ == "__main__":
    main()
