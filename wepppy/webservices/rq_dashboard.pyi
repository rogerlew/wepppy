from __future__ import annotations

from flask import Flask, Response


app: Flask


def dependency_missing() -> Response: ...
