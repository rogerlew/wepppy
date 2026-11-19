"""Microservice-suite adapters for app-level request lifecycle controls."""

from __future__ import annotations

from pathlib import Path

import pytest

import wepppy.microservices.rq_engine as rq_engine


@pytest.fixture(autouse=True)
def _stub_lifecycle_bearer_verification(monkeypatch: pytest.MonkeyPatch) -> None:
    """Keep route auth tests authoritative while bypassing duplicate middleware JWT decode."""
    monkeypatch.setattr(rq_engine, "_verify_lifecycle_bearer", lambda request: None)


@pytest.fixture
def native_csv_converter(tmp_path):
    """Use the exact locally built child; never substitute Python serialization."""
    from wepppy.microservices.parquet_csv import Converter
    from wepppy.microservices.parquet_csv.provenance import generate, inventory, validate
    root = Path(__file__).resolve().parents[2] / 'tools/parquet_csv_cli'
    binary = root / 'rust/target/release/parquet_csv_cli'
    if not binary.is_file():
        # CI builds the same owned source in Dockerfile.test, outside the checkout mount.
        installed = Path('/opt/parquet-csv')
        binary = Path('/usr/local/bin/parquet_csv_cli')
        validate(binary, installed / 'provenance.json', installed)
        assert inventory(installed) == inventory(root), 'Rebuild the native test image for this checkout'
        root = installed
    sidecar = tmp_path / 'parquet_csv_cli.json'
    generate(binary, sidecar, root)
    return Converter(binary, sidecar, tmp_path / 'csv-scratch', source_root=root)
