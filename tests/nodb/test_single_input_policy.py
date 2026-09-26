from types import SimpleNamespace
import pytest
from wepppy.nodb.single_input_policy import (
    EXCLUDED_FEATURES, SingleInputPolicyError, require_feature_allowed,
    require_single_input_policy, require_wepp_input_policy, single_input_uploads_enabled,
)
pytestmark = pytest.mark.unit


def config(flag='True', *, binary='wepp_260803', mods=()):
    return SimpleNamespace(config_get_str=lambda section, key, default=None: flag if key == 'single_user_defined_uploads' else binary,
                           mods=mods, wepp_bin=binary, watershed_instance=SimpleNamespace(mofe_buffer=False))


@pytest.mark.parametrize('flag,expected', [(None, False), ('False', False), ('True', True), ('true', True)])
def test_flag_preserves_absent_and_legacy(flag, expected):
    assert single_input_uploads_enabled(config(flag)) is expected


@pytest.mark.parametrize('flag', ['false-ish', '', 'yes', '1', 'garbage'])
def test_malformed_policy_fails_explicitly(flag):
    with pytest.raises(SingleInputPolicyError):
        single_input_uploads_enabled(config(flag))


@pytest.mark.parametrize('feature', sorted(EXCLUDED_FEATURES))
def test_features_independent_of_current_input_modes(feature):
    with pytest.raises(SingleInputPolicyError):
        require_feature_allowed(config(), feature)
    require_feature_allowed(config(None), feature)


def test_inconsistent_state_and_effective_binary_are_rejected():
    for state in [config(mods=['disturbed']), config(binary='wepp_250217')]:
        with pytest.raises(SingleInputPolicyError):
            require_single_input_policy(state)
    with pytest.raises(SingleInputPolicyError):
        require_single_input_policy(config(), watershed=SimpleNamespace(mofe_buffer=True))
    state = config(); state.wepp_bin = 'wepp_250217'
    with pytest.raises(SingleInputPolicyError):
        require_wepp_input_policy(state)
    with pytest.raises(SingleInputPolicyError):
        require_wepp_input_policy(config(), reveg=True)


def test_compatible_modifiers_remain_allowed():
    for feature in ('ash', 'rap', 'geneva', 'rangeland_cover'):
        require_feature_allowed(config(), feature)


def test_path_guard_reads_parent_run_policy_not_its_solver_dictionary(monkeypatch):
    from types import SimpleNamespace
    from wepppy.nodb.mods.path_ce.path_cost_effective import PathCostEffective
    from wepppy.nodb.single_input_policy import SingleInputPolicyError
    controller = PathCostEffective.__new__(PathCostEffective)
    controller._config = {'sdyd_threshold': 15}
    monkeypatch.setattr(PathCostEffective, 'ron_instance', property(lambda self: SimpleNamespace(
        config_get_str=lambda section, key, default=None: 'True')))
    with pytest.raises(SingleInputPolicyError):
        controller.run()
