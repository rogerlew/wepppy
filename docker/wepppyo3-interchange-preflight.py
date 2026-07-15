#!/usr/bin/env python3
"""Fail service startup unless the paired WEPPpyo3 interchange release is complete."""

from __future__ import annotations

import hashlib
import inspect
import os
from pathlib import Path
import sys
from typing import Sequence


DEFAULT_RELEASE_ROOT = Path("/workdir/wepppyo3/release/linux/py312")


def validate_wepppyo3_interchange() -> tuple[Path, str]:
    configured_root = os.getenv(
        "WEPPPYO3_INTERCHANGE_RELEASE_ROOT",
        str(DEFAULT_RELEASE_ROOT),
    )
    required_root = Path(configured_root).resolve()

    try:
        import wepppyo3  # type: ignore
        import wepppyo3.wepp_interchange as wepp_interchange  # type: ignore

        from wepppy.wepp.interchange._rust_interchange import (
            REQUIRED_WEPPPYO3_INTERCHANGE_API,
        )
    except Exception as exc:  # deliberate service-start import boundary
        print(
            ">>> ERROR: unable to import the required WEPPpyo3 interchange release.",
            file=sys.stderr,
        )
        print(f"    exception: {type(exc).__name__}: {exc}", file=sys.stderr)
        print(f"    required release root: {required_root}", file=sys.stderr)
        raise

    missing = sorted(
        name
        for name in REQUIRED_WEPPPYO3_INTERCHANGE_API
        if not callable(getattr(wepp_interchange, name, None))
    )
    if missing:
        raise RuntimeError(
            f"incomplete WEPPpyo3 interchange API; missing: {', '.join(missing)}"
        )

    extension = Path(wepp_interchange.wepp_interchange_rust.__file__).resolve()
    module_paths = (
        Path(inspect.getfile(wepppyo3)).resolve(),
        Path(inspect.getfile(wepp_interchange)).resolve(),
        extension,
    )
    outside_release = [
        str(path) for path in module_paths if not path.is_relative_to(required_root)
    ]
    if outside_release:
        raise RuntimeError(
            "service requires the configured WEPPpyo3 release; "
            f"unexpected origins: {outside_release}"
        )

    artifact_sha256 = hashlib.sha256(extension.read_bytes()).hexdigest()
    return extension, artifact_sha256


def main(argv: Sequence[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    extension, artifact_sha256 = validate_wepppyo3_interchange()
    print(f">>> WEPPpyo3 interchange import OK: {extension}", flush=True)
    print(f">>> WEPPpyo3 interchange SHA256: {artifact_sha256}", flush=True)

    if args[:1] == ["--"]:
        args.pop(0)
    if args:
        os.execvp(args[0], args)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
