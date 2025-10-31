__all__ = ["build_esdac_soils"]


def build_esdac_soils(*args, **kwargs):
    from .soil_build import build_esdac_soils as _build_esdac_soils

    return _build_esdac_soils(*args, **kwargs)
