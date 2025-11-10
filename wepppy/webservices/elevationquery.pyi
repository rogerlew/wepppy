from __future__ import annotations

from typing import Optional

from flask import Flask, Response


geodata_dir: str
app: Flask


def safe_float_parse(value: object) -> Optional[float]: ...


def health() -> Response: ...


def query_elevation() -> Response: ...
