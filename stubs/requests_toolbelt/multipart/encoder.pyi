from typing import Any, Iterator, Mapping, Sequence, Tuple

FieldsMapping = Mapping[str, Any]
FieldsSequence = Sequence[Tuple[str, Any]]
FieldsType = FieldsMapping | FieldsSequence | None


class MultipartEncoder:
    fields: FieldsType
    boundary: str
    encoding: str
    content_type: str

    def __init__(
        self,
        fields: FieldsType = ...,
        *,
        boundary: str | None = ...,
        encoding: str | None = ...,
    ) -> None: ...

    def to_string(self) -> bytes: ...
    def read(self, size: int | None = ...) -> bytes: ...
    def __iter__(self) -> Iterator[bytes]: ...
    def __len__(self) -> int: ...
    def reset(self) -> None: ...
