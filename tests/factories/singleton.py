"""Utilities for constructing lightweight singleton stubs."""

from __future__ import annotations

import copy
from contextlib import contextmanager
from typing import Any, Dict, Iterable, Tuple, Type


class LockedMixin:
    """Adds a ``locked`` context manager that mirrors NoDb behaviour."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)  # type: ignore[misc]
        self._lock_calls = 0

    @contextmanager
    def locked(self):
        self._lock_calls += 1
        yield


class ParseInputsRecorderMixin:
    """Records payloads provided to ``parse_inputs``."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)  # type: ignore[misc]
        self.parse_inputs_calls = []

    def parse_inputs(self, payload):  # noqa: ANN001 - mirror signature
        self.parse_inputs_calls.append(payload)
        return payload


def singleton_factory(
    name: str,
    /,
    *,
    attrs: Dict[str, Any] | None = None,
    methods: Dict[str, Any] | None = None,
    mixins: Iterable[Type[Any]] = (),
) -> Type[Any]:
    """Create a singleton class with NoDb-like semantics."""

    attrs = attrs or {}
    methods = methods or {}
    bases: Tuple[Type[Any], ...] = tuple(mixins) + (object,)

    mixin_tuple = tuple(mixins)

    class_dict: Dict[str, Any] = {
        "_instances": {},
        "_defaults": attrs,
    }

    def __init__(self, wd: str, **overrides: Any) -> None:
        for mixin in mixin_tuple:
            init = getattr(mixin, "__init__", None)
            if init:
                init(self)
        self.wd = wd
        defaults = copy.deepcopy(self._defaults)  # type: ignore[attr-defined]
        defaults.update(overrides)
        for key, value in defaults.items():
            setattr(self, key, value)

    @classmethod
    def getInstance(cls, wd: str):
        instance = cls._instances.get(wd)  # type: ignore[attr-defined]
        if instance is None:
            instance = cls(wd)
            cls._instances[wd] = instance  # type: ignore[attr-defined]
        return instance

    @classmethod
    def reset_instances(cls):
        cls._instances.clear()  # type: ignore[attr-defined]

    class_dict["__init__"] = __init__
    class_dict["getInstance"] = getInstance
    class_dict["reset_instances"] = reset_instances
    class_dict.update(methods)

    return type(name, bases, class_dict)
