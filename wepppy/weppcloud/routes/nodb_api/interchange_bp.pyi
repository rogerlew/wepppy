from __future__ import annotations

from typing import Any, MutableMapping, Optional

from flask import Blueprint, Response

interchange_bp: Blueprint

def _sanitize_subpath(value: Optional[str]) -> Optional[str]: ...

def _enqueue_interchange_job(runid: str, config: str, wepp_output_subpath: Optional[str]) -> Response: ...

def migrate_default_interchange(runid: str, config: str) -> Response | tuple[Response, int]: ...
