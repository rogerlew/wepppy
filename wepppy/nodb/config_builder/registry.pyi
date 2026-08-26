from pathlib import Path
from wepppy.nodb.config_builder.schema import Registry

__all__ = ["DEFAULT_PROFILES_ROOT", "RegistryError", "load_registry"]
DEFAULT_PROFILES_ROOT: Path

class RegistryError(ValueError): ...

def load_registry(root: str | Path = ...) -> Registry: ...
