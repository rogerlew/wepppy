from __future__ import annotations

from flask import Blueprint, Response

debris_flow_bp: Blueprint

def report_debris_flow(runid: str, config: str) -> Response: ...
