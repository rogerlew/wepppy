from __future__ import annotations

import importlib
import json
from typing import Any, Mapping

from wepppy.nodb.mods.geneva.errors import GenevaKernelError


class GenevaKernelGateway:
    """Typed boundary for Geneva Rust kernel entrypoints."""

    _MODULE_NAME = "wepppyo3.climate.cli_revision_rust"

    def call_json_api(self, api_name: str, payload: Mapping[str, Any]) -> dict[str, Any]:
        module = self._load_kernel_module(api_name)
        request_text = json.dumps(payload, sort_keys=True)

        api = getattr(module, api_name, None)
        if api is None or not callable(api):
            raise GenevaKernelError(
                f"Geneva kernel API '{api_name}' is unavailable.",
                code="missing_dependency",
                details={"module": self._MODULE_NAME, "api": api_name},
                status_code=500,
            )

        try:
            response_text = api(request_text)
        except ValueError as exc:
            code, details = _parse_kernel_value_error(str(exc))
            raise GenevaKernelError(
                f"Geneva kernel call '{api_name}' failed.",
                code=code,
                details=details,
            ) from exc

        try:
            parsed = json.loads(response_text)
        except (TypeError, json.JSONDecodeError) as exc:
            raise GenevaKernelError(
                f"Geneva kernel returned invalid JSON for '{api_name}'.",
                code="serialization_error",
                details=str(exc),
                status_code=500,
            ) from exc

        if not isinstance(parsed, dict):
            raise GenevaKernelError(
                f"Geneva kernel returned non-object payload for '{api_name}'.",
                code="serialization_error",
                details={"api": api_name, "type": type(parsed).__name__},
                status_code=500,
            )

        return parsed

    def _load_kernel_module(self, api_name: str):
        try:
            return importlib.import_module(self._MODULE_NAME)
        except ImportError as exc:
            raise GenevaKernelError(
                "Geneva kernel bindings are unavailable. Expected wepppyo3.climate.cli_revision_rust.",
                code="missing_dependency",
                details={"module": self._MODULE_NAME, "api": api_name},
                status_code=500,
            ) from exc


def _parse_kernel_value_error(message: str) -> tuple[str, dict[str, Any]]:
    text = str(message).strip()
    if not text:
        return "kernel_validation_error", {"message": "Kernel raised empty ValueError"}

    if ":" in text:
        maybe_code, remainder = text.split(":", 1)
        code = maybe_code.strip()
        detail = remainder.strip()
        if code:
            return code, {"message": detail or text}

    return "kernel_validation_error", {"message": text}


__all__ = ["GenevaKernelGateway"]
