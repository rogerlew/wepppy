"""Synthetic source setup shared by real subsystem failure-output tests."""
from wepppy.observability import safe_logging
from wepppy.observability.safe_traceback import SecretSourceProfile, SecretSourceSpec


def install_canary(monkeypatch, tmp_path):
    canary = 'f5-subsystem-canary-48351ac'
    source = tmp_path / 'diagnostic-secret'
    source.write_text(canary)
    monkeypatch.setenv('F5_DIAGNOSTIC_FILE', str(source))
    monkeypatch.setattr(safe_logging, '_PROFILE', SecretSourceProfile('subsystem-test', (
        SecretSourceSpec(None, 'F5_DIAGNOSTIC_FILE'),)))
    return canary
