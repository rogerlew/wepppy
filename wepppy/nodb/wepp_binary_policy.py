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
    multiple = bool(getattr(config, 'multi_ofe', False)) if multi_ofe is None else multi_ofe
    if not flattened and not uploads and not multiple:
        return None
    # Validate stored metadata, but geometry never determines executable support.
    # Builder geometry authorization is enforced separately from this selector.
    capability_authority(config)
    for axis in ('wepp_binaries', 'delineation_backends', 'watershed_representations'):
        capability_ids(config, axis)
    return get_compatible_wepp_bin_opts(multi_ofe=multiple, single_user_defined_inputs=uploads)


def validate_project_wepp_binary_selection(wepp, requested, *, backend=None):
    """Preserve omission/current legacy state; validate explicit changes before writes."""
    if requested is None or requested == getattr(wepp, 'wepp_bin', None):
        return
    choices = project_wepp_binary_options(wepp, backend=backend)
    if choices is not None and requested not in choices:
        raise ValueError('WEPP executable is not installed or does not support this project: ' + repr(requested))
