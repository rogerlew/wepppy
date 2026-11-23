"""Expose the image's locked browser assets to the mounted CI candidate."""
from pathlib import Path
import hashlib


def prepare(source: Path, installed: Path) -> None:
    """Require candidate-matching image assets and reject foreign directories."""
    for name in ("package.json", "package-lock.json"):
        if hashlib.sha256((source / name).read_bytes()).digest() != hashlib.sha256((installed / name).read_bytes()).digest():
            raise RuntimeError(f"CI image {name} differs from candidate; rebuild the test image")
    for name, target in (("node_modules", installed / "node_modules"),
                         (".playwright-browsers", installed / "browsers")):
        if not target.is_dir():
            raise RuntimeError(f"Required CI image assets missing: {target}")
        link = source / name
        if link.is_symlink():
            if link.resolve() != target:
                raise RuntimeError(f"Unexpected CI runtime symlink: {link}")
        elif not link.exists():
            link.symlink_to(target, target_is_directory=True)
        else:
            raise RuntimeError(f"CI runtime requires image-owned assets; remove existing path and retry: {link}")
    print("CI browser asset manifests match candidate; runtime assets prepared")


def main() -> None:
    prepare(Path(__file__).resolve().parents[1] / "wepppy/weppcloud/static-src",
            Path("/opt/wepppy-ci"))


if __name__ == "__main__":
    main()
