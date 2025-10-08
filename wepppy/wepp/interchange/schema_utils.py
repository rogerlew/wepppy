from __future__ import annotations

from typing import Dict

import pyarrow as pa

def pa_field(name: str, dtype: pa.DataType, *, units: str | None = None, description: str | None = None) -> pa.Field:
    metadata: Dict[bytes, bytes] = {}
    if units is not None:
        metadata[b"units"] = units.encode()
    if description is not None:
        metadata[b"description"] = description.encode()
    if metadata:
        return pa.field(name, dtype).with_metadata(metadata)
    return pa.field(name, dtype)
