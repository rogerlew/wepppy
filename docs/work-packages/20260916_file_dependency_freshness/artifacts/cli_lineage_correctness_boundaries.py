"""Actual current producer errors/access behavior on a disposable project."""
import json
import logging
import os
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace

from tests.nodb.test_climate_artifact_export_service import _write_minimal_cli
from wepppy.nodb.core.climate_artifact_export_service import ClimateArtifactExportService


def main():
    results = {"uid": os.getuid(), "cases": {}}
    with TemporaryDirectory(prefix="cli-lineage-correctness-") as temporary:
        root = Path(temporary)
        directory = root / "climate"
        directory.mkdir()
        source = directory / "selected.cli"
        _write_minimal_cli(source)
        climate = SimpleNamespace(wd=str(root), cli_dir=str(directory), cli_fn=source.name,
                                  logger=logging.getLogger("cli-lineage-correctness"))
        service = ClimateArtifactExportService()
        output = service.export_cli_parquet(climate)
        original_output = output.read_bytes()
        original_source = source.read_bytes()
        invalid_header = original_source.replace(b"dur", b"bad")
        assert invalid_header != original_source
        for label, data in (("empty_cli", b""), ("invalid_header", invalid_header)):
            source.write_bytes(data)
            try:
                result = service.export_cli_parquet(climate)
            except (IndexError, AssertionError, OSError, ValueError) as error:
                results["cases"][label] = {"raised": type(error).__name__, "message": str(error)}
            else:
                results["cases"][label] = {"returned": str(result) if result is not None else None}
            results["cases"][label]["prior_output_unchanged"] = output.read_bytes() == original_output
        source.write_bytes(original_source)
        assert os.getuid() != 0
        output.chmod(0o444)
        try:
            result = service.export_cli_parquet(climate)
            results["cases"]["readonly_output_writable_parent"] = {
                "returned": str(result) if result is not None else None,
                "prior_output_unchanged": output.read_bytes() == original_output,
                "parent_writable": os.access(directory, os.W_OK)}
        finally:
            output.chmod(0o644)
    encoded = json.dumps(results, indent=2)
    print(encoded)
    Path(__file__).with_suffix(".json").write_text(encoded + "\n")


if __name__ == "__main__":
    main()
