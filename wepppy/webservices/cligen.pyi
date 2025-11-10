from __future__ import annotations

from typing import Dict, Optional, Union

from flask import Flask, Request, Response


app: Flask
static_dir: Optional[str]


def safe_float_parse(value: object) -> Optional[float]: ...


def health() -> Response: ...


def findstation() -> Response: ...


def _fetch_par_contents(par: str, _request: Request) -> Union[str, Response]: ...


def fetchstationmeta(par: str) -> Response: ...


def fetchpar(par: str) -> Response: ...


def single_year_route(par: str) -> Response: ...


def multiple_year_route(par: str) -> Response: ...


def _multiple_year(par: str, _request: Request, singleyearmode: bool = ...) -> Response: ...


def _make_single_storm_clinp(
    wd: str,
    cli_fn: str,
    par_fn: str,
    cliver: str,
    kwds: Dict[str, object],
) -> None: ...


def single_storm(par: str) -> Response: ...


def future_rcp85(par: str) -> Response: ...
