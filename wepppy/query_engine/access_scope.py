"""Carry an HTTP admission boundary through synchronous catalog/query work.

Non-HTTP callers retain their existing policy. The scoped checks run before
native scans/schema reads, not merely when filtering the returned catalog.
"""
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass
from pathlib import Path
from collections.abc import Callable
import os


@dataclass(frozen=True)
class AccessScope:
    root: Path
    parent: Path
    checkpoint: Callable[[], None]

    def require_path(self, path: Path) -> None:
        resolved = path.resolve()
        allowed = [self.root]
        if self.parent != self.root:
            allowed.extend(self.parent / name for name in ('climate', 'dem', 'watershed', 'landuse', 'soils', 'wepp/runs'))
            # Exact metadata links produced by OmniCloneContrastService.
            if resolved in {self.parent / name for name in ('dem.nodb', 'climate.nodb', 'watershed.nodb',
                    'landuse.nodb', 'soils.nodb', 'unitizer.nodb', 'treatments.nodb',
                    'climate.nodir', 'watershed.nodir')}:
                return
        if not any(resolved.is_relative_to(root) for root in allowed):
            raise PermissionError('Dataset outside authorized resource')

    def source_path(self, path: Path, recorded_root: str | None = None) -> Path:
        """Relocate retained absolute metadata lexically; never open the old root."""
        if '..' in path.parts:
            raise PermissionError('Dataset outside authorized resource')
        selected = path if path.is_absolute() else self.root / path
        try:
            self.require_path(selected)
            return selected
        except PermissionError:
            if not path.is_absolute() or not recorded_root or recorded_root == str(self.root):
                raise
        old_root = Path(recorded_root)
        if not old_root.is_absolute() or '..' in old_root.parts:
            raise PermissionError('Invalid catalog root')
        if path.is_relative_to(old_root):
            selected = self.root / path.relative_to(old_root)
        elif self.parent != self.root:
            suffix = self.root.relative_to(self.parent).parts
            if tuple(old_root.parts[-len(suffix):]) != suffix:
                raise PermissionError('Invalid catalog parent')
            old_parent = Path(*old_root.parts[:-len(suffix)])
            selected = self.parent / path.relative_to(old_parent)
        else:
            raise PermissionError('Dataset outside authorized resource')
        self.require_path(selected)
        return selected

    def before_scan(self, directory: Path) -> None:
        self.checkpoint()
        # Match the native scanner's legacy skip boundary, then narrow sources
        # it would actually consume. External DEM symlinks are intentionally
        # skipped by the native scanner and must not break unrelated queries.
        native_roots = [directory]
        if '_pups' in directory.parts:
            index = directory.parts.index('_pups')
            native_roots.append(Path(*directory.parts[:index]))
        stack = [directory]
        seen = set()
        while stack:
            current = stack.pop()
            self.require_path(current)
            resolved = current.resolve()
            if resolved in seen:
                continue
            seen.add(resolved)
            with os.scandir(current) as entries:
                for entry in entries:
                    path = Path(entry.path)
                    if entry.is_symlink():
                        resolved_entry = path.resolve()
                        if not any(resolved_entry.is_relative_to(root) for root in native_roots):
                            continue
                        self.require_path(path)
                    if entry.is_dir():
                        stack.append(path)


_CURRENT_SCOPE: ContextVar[AccessScope | None] = ContextVar('query_access_scope', default=None)


def current_scope() -> AccessScope | None:
    return _CURRENT_SCOPE.get()


def check_source(path: Path) -> None:
    scope = current_scope()
    if scope is not None:
        scope.require_path(path)


@contextmanager
def access_scope(root: Path, parent: Path, checkpoint: Callable[[], None]):
    token = _CURRENT_SCOPE.set(AccessScope(root, parent, checkpoint))
    try:
        yield
    finally:
        _CURRENT_SCOPE.reset(token)
