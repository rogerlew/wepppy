# 2026-05-13 Release Refresh (`raster_characteristics`)

Evidence class: `Ran`

## Build and Copy

Working directory: `/home/workdir/wepppyo3`

Commands:

```sh
export PYO3_PYTHON=/usr/bin/python3.12
export PYTHON_SYS_EXECUTABLE=$PYO3_PYTHON
cargo build -p raster_characteristics_rust --release
cp target/release/libraster_characteristics_rust.so \
  release/linux/py312/wepppyo3/raster_characteristics/raster_characteristics_rust.so
```

Result: build and copy succeeded.

## Runtime Import Proof

Command:

```sh
PYTHONPATH=/home/workdir/wepppyo3/release/linux/py312 python3.12 -c \
  "from wepppyo3.raster_characteristics import raster_characteristics_rust as rc; print(rc.__file__)"
```

Observed output:

```text
/home/workdir/wepppyo3/release/linux/py312/wepppyo3/raster_characteristics/raster_characteristics_rust.so
```

## SHA256

Command:

```sh
sha256sum release/linux/py312/wepppyo3/raster_characteristics/raster_characteristics_rust.so
```

Observed output:

```text
a2dddb70c3c9670bad8c4103b64d455539896d5ea1be17a99d9c5adc88dccda6  release/linux/py312/wepppyo3/raster_characteristics/raster_characteristics_rust.so
```
