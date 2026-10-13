"""Live executable availability without changing project-owned geometry or config."""
from __future__ import annotations

from wepp_runner.wepp_binary_capabilities import get_compatible_wepp_bin_opts
from wepppy.nodb.project_config_capabilities import capability_authority, capability_ids
from wepppy.nodb.single_input_policy import single_input_uploads_enabled

__all__ = ['project_wepp_binary_options', 'validate_project_wepp_binary_selection']


def project_wepp_binary_options(config, *, multi_ofe=None, backend=None):
    """Return governed live choices, or None for ordinary legacy selection."""
    getter = getattr(config, 'config_get_bool', None)
    flattened = bool(getter('config', 'flattened', False)) if getter else False
    uploads = single_input_uploads_enabled(config)
    if not flattened and not uploads:
        return None
    authority = capability_authority(config)
    # Validate legacy axis shape even though its old population no longer pins releases.
    capability_ids(config, 'wepp_binaries')
    multiple = bool(getattr(config, 'multi_ofe', False)) if multi_ofe is None else multi_ofe
    backends = authority.delineation_backends if authority else capability_ids(config, 'delineation_backends')
    representations = authority.watershed_representations if authority else capability_ids(config, 'watershed_representations')
    if backend is None and (backends is not None or multiple):
        watershed = config.watershed_instance
        value = getattr(watershed, 'delineation_backend', None)
        backend = str(getattr(value, 'name', value) or '').lower()
        if not backend and authority is not None:
            backend = authority.defaults['delineation_backend']
    representation = 'multiple-ofe' if multiple else 'single-ofe'
    if ((backends is not None and backend not in backends)
            or (representations is not None and representation not in representations)
            or (multiple and backend != 'wbt')):
        return ()
    return get_compatible_wepp_bin_opts(multi_ofe=multiple, single_user_defined_inputs=uploads)


def validate_project_wepp_binary_selection(wepp, requested, *, backend=None):
    """Preserve omission/current legacy state; validate explicit changes before writes."""
    if requested is None or requested == getattr(wepp, 'wepp_bin', None):
        return
    choices = project_wepp_binary_options(wepp, backend=backend)
    if choices is not None and requested not in choices:
        raise ValueError('WEPP executable is not installed or does not support this project: ' + repr(requested))
