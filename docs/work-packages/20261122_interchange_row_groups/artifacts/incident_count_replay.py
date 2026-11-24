"""Repeat one observed day under 47,582 source IDs and verify the daily reduction."""
import argparse
from pathlib import Path
from tempfile import TemporaryDirectory

import numpy as np
import pyarrow.parquet as pq
import wepppyo3.wepp_interchange as native


def main(raw: Path) -> None:
    count = 47_582
    with TemporaryDirectory() as scratch:
        root = Path(scratch)
        reference = {}
        outputs = {}
        for family in ("pass", "wat"):
            sample = root / family
            with (raw / f"H1.{family}.dat").open() as source, sample.open("w") as out:
                for line in source:
                    out.write(line)
                    if line.startswith("SUBEVENT") or line.split()[:3] == ["1", "1", "1981"]:
                        break
            sources = []
            for hill in range(1, count + 1):
                path = root / f"H{hill}.{family}.dat"
                path.symlink_to(sample)
                sources.append(str(path))
            reference[family] = str(root / f"one.{family}.parquet")
            outputs[family] = str(root / f"H.{family}.parquet")
            writer = getattr(native, f"hillslope_{family}_files_to_parquet")
            writer(sources[:1], reference[family], 1, 2)
            summary = writer(sources, outputs[family], 1, 2)
            assert summary["rows_written"] == count and summary["row_groups"] == 15861
            print(family, summary, flush=True)

        def daily(inputs, selected):
            output = root / "daily.parquet"
            native.totalwatsed3_to_parquet(inputs["pass"], inputs["wat"], str(output),
                                            0.0, 0.04, 0.0, 1, 2, wepp_ids=selected)
            data = pq.read_table(output)
            assert (data.num_rows, data.num_columns) == (1, 79)
            return data.to_pylist()[0]

        one = daily(reference, None)
        for selected, multiplier in [(None, count), ([1, 32768, count], 3)]:
            result = daily(outputs, selected)
            for column in ("Area", "sbrunv"):
                np.testing.assert_allclose(result[column], one[column] * multiplier, rtol=1e-10)
            for column in ("Runoff", "year", "julian"):
                np.testing.assert_allclose(result[column], one[column], rtol=1e-10)
            print(multiplier, {key: result[key] for key in ("Area", "sbrunv", "Runoff")}, flush=True)


        # AgFields has an additional logical identity and manifest validation layer.
        from wepppy.wepp.interchange import ag_fields_interchange as ag_fields

        mapping = {hill: (hill - 1) // 5 + 1 for hill in range(1, count + 1)}
        descriptors = []
        for hill, field in mapping.items():
            path = root / f"H{hill}.loss.dat"
            path.symlink_to(raw / "H1.loss.dat")
            descriptors.append((str(path), field, hill))
        output = root / "H.loss.parquet"
        native_summary = native.ag_fields_hillslope_loss_files_to_parquet(
            descriptors, str(output), 1, 2
        )
        summary = ag_fields._validate_output(output, ag_fields.LOSS_SCHEMA, mapping, set())
        assert summary["row_groups"] == native_summary["row_groups"] < 32768
        assert summary["identity_count"] == count
        assert summary["rows"] == count * 5
        print("AgFields LOSS", summary, flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("raw_output", type=Path, help="directory containing the incident H1 reports")
    main(parser.parse_args().raw_output.resolve())
