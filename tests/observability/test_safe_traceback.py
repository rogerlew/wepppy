"""Canary tests read final diagnostics, never real deployment secrets."""
import json
from pathlib import Path
from urllib.parse import quote, quote_plus

import pytest

from wepppy.observability import safe_traceback as safe
from wepppy.observability import secret_profiles as profiles

pytestmark = pytest.mark.unit


@pytest.fixture
def source(tmp_path, monkeypatch):
    path = tmp_path / 'secret'
    value = 'canary-quote" /\\\n雪-9137'
    path.write_text(value)
    monkeypatch.setenv('F5_TEST_FILE', str(path))
    return path, value, safe.SecretSourceProfile('test', (safe.SecretSourceSpec('F5_TEST', 'F5_TEST_FILE'),))


def test_final_trace_preserves_context_and_filters_variants(source):
    _, value, profile = source
    variants = [value, quote(value, safe=''), quote_plus(value), json.dumps(value)[1:-1], repr(value)[1:-1]]
    try:
        try:
            raise ValueError('cause ' + ' | '.join(variants))
        except ValueError as cause:
            outer = RuntimeError('safe contextual message')
            outer.add_note('note ' + value)
            raise outer from cause
    except RuntimeError as exc:
        text = safe.render_exception(exc, source_profile=profile)
    assert 'safe contextual message' in text
    assert 'ValueError' in text and 'RuntimeError' in text
    assert str(Path(__file__).resolve()) in text
    assert 'test_final_trace_preserves_context_and_filters_variants' in text
    assert 'direct cause' in text
    assert all(variant not in text for variant in variants)
    assert '[REDACTED]' in text


def test_group_and_locals(source):
    _, value, profile = source
    local_only_secret = 'local-only-not-a-source-53731'
    try:
        raise ExceptionGroup('group ' + value, [ValueError(value), RuntimeError('safe sibling')])
    except ExceptionGroup as exc:
        text = safe.render_exception(exc, source_profile=profile)
    assert value not in text
    assert local_only_secret not in text
    assert 'ExceptionGroup' in text and 'safe sibling' in text


def test_keyring_and_replacement(tmp_path, monkeypatch):
    path = tmp_path / 'keys'
    path.write_text(' member-one-secret , member-two-secret ')
    monkeypatch.setenv('F5_RING_FILE', str(path))
    profile = safe.SecretSourceProfile('test', (safe.SecretSourceSpec('F5_RING', 'F5_RING_FILE', decoder='comma'),))
    text = safe.safe_text('member-one-secret member-two-secret', source_profile=profile)
    assert 'member-one-secret' not in text and 'member-two-secret' not in text
    path.write_text('replacement-member-53713')
    assert safe.safe_text('replacement-member-53713', source_profile=profile) == safe.REDACTED
    assert not any(isinstance(v, safe._Snapshot) for v in vars(safe).values())


@pytest.mark.parametrize('state', ['missing', 'empty', 'oversize', 'unicode'])
def test_source_failure_never_returns_raw(source, state):
    path, value, profile = source
    if state == 'missing':
        path.unlink()
    elif state == 'empty':
        path.write_text('')
    elif state == 'oversize':
        path.write_text('x' * (safe.MAX_SOURCE + 1))
    else:
        path.write_bytes(b'\xff')
    assert safe.render_exception(ValueError(value), source_profile=profile, error_id='caller-secret') == safe.UNAVAILABLE


def test_structural_unknown_credentials():
    value = ('https://alice:uri-credential@host/path\n'
             'Authorization: Bearer header-credential\n'
             'Cookie: session=cookie-credential\n'
             '{"password": "dict-credential", "safe": "context"}\n'
             'Bearer standalone-credential\n'
             'eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiJ4In0.signature\n'
             '-----BEGIN PRIVATE KEY-----\nprivate-body\n-----END PRIVATE KEY-----')
    text = safe.safe_text(value, source_profile=profiles.SHAPE)
    for canary in ('uri-credential', 'header-credential', 'cookie-credential', 'dict-credential',
                   'standalone-credential', 'eyJhbGci', 'private-body'):
        assert canary not in text
    assert 'host/path' in text and 'context' in text


def test_explicit_profiles_exclude_downstream_paths(monkeypatch):
    monkeypatch.setenv('WEPPCLOUDR_K8S_IDENTITY_TOKEN_FILE', '/definitely/missing/downstream')
    monkeypatch.setenv('REDIS_PASSWORD_FILE', '/definitely/missing/stale')
    assert safe.safe_text('useful diagnostic', source_profile=profiles.SHAPE) == 'useful diagnostic'
    # Narrow the web profile to the inspected metadata to avoid real environment sources.
    assert all(spec.file_setting != 'WEPPCLOUDR_K8S_IDENTITY_TOKEN_FILE' for spec in profiles.WEB.sources)


def test_no_exception_does_not_load_sources(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError('no snapshot should be acquired')
    monkeypatch.setattr(safe, '_snapshot', forbidden)
    assert safe.render_current_exception(source_profile=profiles.WEB) == 'NoneType: None\n'


def test_legacy_url_constituents(monkeypatch):
    monkeypatch.setenv('F5_URL', 'postgres://user:encoded%2Fcredential@db/main')
    profile = safe.SecretSourceProfile('test', (safe.SecretSourceSpec('F5_URL', decoder='url'),))
    assert 'encoded/credential' not in safe.safe_text('encoded/credential', source_profile=profile)


def test_structure_and_bounds(source):
    _, value, profile = source
    output = safe.safe_structure({'message': value, 'details': [value, 123, None]}, source_profile=profile)
    assert output == {'message': safe.REDACTED, 'details': [safe.REDACTED, 123, None]}
    assert safe.safe_text('x' * (safe.MAX_TEXT + 1), source_profile=profile) == safe.UNAVAILABLE
    cycle = []
    cycle.append(cycle)
    assert safe.safe_structure(cycle, source_profile=profile) == safe.UNAVAILABLE


def test_renderer_internal_failure(source, monkeypatch):
    _, value, profile = source
    def broken(*args):
        raise RuntimeError(value)
    monkeypatch.setattr(safe, 'sanitize_text', broken)
    assert safe.render_exception(ValueError(value), source_profile=profile) == safe.UNAVAILABLE


def test_structural_mapping_credentials_and_schema_keys(monkeypatch):
    assert safe.safe_structure({'password': 'unknown-secret', 'Authorization': 'Bearer unknown-token'},
                               source_profile=profiles.SHAPE) == {'password': safe.REDACTED, 'Authorization': safe.REDACTED}
    monkeypatch.setenv('F5_SCHEMA', 'message')
    profile = safe.SecretSourceProfile('schema', (safe.SecretSourceSpec('F5_SCHEMA'),))
    assert safe.safe_diagnostics(source_profile=profile, message='safe') == {'message': 'safe'}
    assert safe.safe_structure({'message': 1, safe.REDACTED: 2}, source_profile=profile) == safe.UNAVAILABLE


def test_consumer_url_precedence_and_redis_framing(tmp_path, monkeypatch):
    monkeypatch.setenv('SQLALCHEMY_DATABASE_URI', 'postgresql://user:slash/credential@db/main')
    monkeypatch.setenv('POSTGRES_PASSWORD_FILE', str(tmp_path / 'stale-unused'))
    monkeypatch.setenv('DATABASE_URL', 'malformed-unused')
    profile = safe.SecretSourceProfile('db', profiles.DATABASE)
    assert safe.safe_text('slash/credential', source_profile=profile) == safe.REDACTED
    monkeypatch.delenv('REDIS_PASSWORD_FILE', raising=False)
    monkeypatch.setenv('REDIS_PASSWORD', '  trimmed-secret\n')
    profile = safe.SecretSourceProfile('redis', (profiles.REDIS[0],))
    assert safe.safe_text('trimmed-secret', source_profile=profile) == safe.REDACTED


def test_bare_noncanonical_jwt_and_aggregate_bound():
    import base64
    header = base64.urlsafe_b64encode(b' {"alg":"HS256"}').decode().rstrip('=')
    token = header + '.eyJzdWIiOiJ4In0.signaturesignature'
    assert safe.safe_text(token, source_profile=profiles.SHAPE) == safe.REDACTED
    assert safe.safe_structure(['x' * 600_000, 'y' * 600_000], source_profile=profiles.SHAPE) == safe.UNAVAILABLE
    assert safe.safe_structure([ValueError('x' * 600_000), ValueError('y' * 600_000)], source_profile=profiles.SHAPE) == safe.UNAVAILABLE


def test_mixed_percent_encoding_and_short_jwt(monkeypatch):
    import base64
    monkeypatch.setenv('F5_MIXED', 'mixed/:credential')
    profile = safe.SecretSourceProfile('mixed', (safe.SecretSourceSpec('F5_MIXED'),))
    assert safe.safe_text('mixed%2f%3Acredential', source_profile=profile) == safe.REDACTED
    header = base64.urlsafe_b64encode(b'{"alg":"HS256"}').decode().rstrip('=')
    assert safe.safe_text(header + '.e30.signature', source_profile=profiles.SHAPE) == safe.REDACTED
    context = 'longmodulename.longclassname.longmethodname'
    assert safe.safe_text(context, source_profile=profiles.SHAPE) == context


@pytest.mark.timeout(5)
def test_adversarial_structural_scan_is_bounded():
    for token in ('password', 'password-secret-'):
        text = token * 50_000
        assert safe.safe_text(text, source_profile=profiles.SHAPE) == text
    plain = 'x' * 900_000
    assert safe.safe_text(plain, source_profile=profiles.SHAPE) == plain
    malformed_pem = '-----BEGIN PRIVATE KEY-----\n' * 20_000
    assert safe.safe_text(malformed_pem, source_profile=profiles.SHAPE) == safe.REDACTED


def test_redis_url_alias_precedence(monkeypatch):
    monkeypatch.setenv('REDIS_URL', 'redis://user:active-secret@cache/0')
    monkeypatch.setenv('RQ_REDIS_URL', 'ignored-malformed')
    monkeypatch.setenv('SESSION_REDIS_URL', 'ignored-by-nonsession')
    monkeypatch.delenv('REDIS_PASSWORD_FILE', raising=False)
    profile = safe.SecretSourceProfile('redis', profiles.REDIS)
    assert safe.safe_text('active-secret', source_profile=profile) == safe.REDACTED


def test_file_only_source_does_not_invent_env_fallback(monkeypatch):
    monkeypatch.setenv('WEPPCLOUDR_CONTROL_PLANE_TOKEN', 'not-consumed')
    monkeypatch.delenv('WEPPCLOUDR_CONTROL_PLANE_TOKEN_FILE', raising=False)
    source = next(spec for spec in profiles.CONTROL_PLANE.sources if spec.file_setting == 'WEPPCLOUDR_CONTROL_PLANE_TOKEN_FILE')
    assert safe.safe_text('context', source_profile=safe.SecretSourceProfile('control', (source,))) == safe.UNAVAILABLE


@pytest.mark.parametrize('text', ['ValueError: password=unknown-canary',
                                  'message: password=unknown-canary',
                                  '{"safe": "password=unknown-canary"}'])
def test_structural_assignment_after_nonsensitive_prefix(text):
    assert 'unknown-canary' not in safe.safe_text(text, source_profile=profiles.SHAPE)


def test_optional_package_source_is_metadata_only_and_reads_current_file(tmp_path, monkeypatch):
    from types import SimpleNamespace
    package = tmp_path / 'package'
    package.mkdir()
    source = package / '.token'
    monkeypatch.setattr(safe.PathFinder, 'find_spec', lambda name: SimpleNamespace(
        submodule_search_locations=[str(package)]))
    profile = safe.SecretSourceProfile('package', (
        safe.SecretSourceSpec(None, package_file=('explicit_package', '.token')),))
    assert safe.safe_text('context', source_profile=profile) == 'context'
    source.write_text('first-package-canary')
    assert safe.safe_text('first-package-canary', source_profile=profile) == safe.REDACTED
    source.write_text('second-package-canary')
    assert safe.safe_text('second-package-canary', source_profile=profile) == safe.REDACTED
    source.unlink()
    source.mkdir()
    assert safe.safe_text('context', source_profile=profile) == safe.UNAVAILABLE
