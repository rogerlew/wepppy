from __future__ import annotations

from typing import Any, Callable, Sequence

def encode(
    value: Any,
    *,
    unpicklable: bool = ...,
    make_refs: bool = ...,
    keys: bool = ...,
    max_depth: int | None = ...,
    reset: bool = ...,
    backend: str | None = ...,
    warn: bool = ...,
    context: Any = ...,
    max_iter: int | None = ...,
    use_decimal: bool = ...,
    numeric_keys: bool = ...,
    use_base85: bool = ...,
    fail_safe: Callable[[Any], Any] | None = ...,
    indent: int | tuple[int, int] | str | None = ...,
    separators: tuple[str, str] | None = ...,
    include_properties: bool = ...,
    handle_readonly: bool = ...,
) -> str: ...


def decode(
    string: str | bytes | bytearray,
    *,
    backend: str | None = ...,
    context: Any = ...,
    keys: bool = ...,
    reset: bool = ...,
    safe: bool = ...,
    classes: Sequence[str] | None = ...,
    v1_decode: bool = ...,
    on_missing: str = ...,
    handle_readonly: bool = ...,
) -> Any: ...
