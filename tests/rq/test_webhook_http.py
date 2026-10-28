from datetime import datetime, timezone

import pytest

from wepppy.rq.webhook_http import InvalidDestination, destination, public_address, retry_after, deliver

pytestmark = pytest.mark.unit


@pytest.mark.parametrize('url', [None, '', [], 'http://example.com/', 'https://user:secret@example.com/',
    'https://example.com:8443/', 'https://127.0.0.1/', 'https://[::1]/', 'https://example.com/#fragment',
    'https://example.com/\r\nX: leak', 'https://example.com\\@evil.com/', 'https://example.com./'])
def test_invalid_destination_is_sanitized(url):
    with pytest.raises(InvalidDestination) as exc:
        destination(url)
    assert 'secret' not in str(exc.value)


def test_valid_destination_preserves_capability_without_header_injection():
    result = destination('https://Example.com/capability/path?token=private')
    assert result.host == 'example.com'
    assert result.target == '/capability/path?token=private'


@pytest.mark.parametrize('address', ['127.0.0.1', '10.0.0.1', '169.254.169.254', '0.0.0.0', '224.0.0.1',
    '::1', 'fc00::1', 'fe80::1', '::ffff:127.0.0.1', '2002:7f00:1::', '64:ff9b::7f00:1', '192.0.2.1'])
def test_private_and_transition_addresses_are_rejected(address):
    assert not public_address(address)


def test_public_address_and_retry_after():
    assert public_address('8.8.8.8')
    assert public_address('2606:4700:4700::1111')
    assert retry_after('999999') == 300
    assert retry_after('nonsense') is None
    assert retry_after('Wed, 28 Oct 2026 20:00:30 GMT', datetime(2026, 10, 28, 20, tzinfo=timezone.utc)) == 30


@pytest.mark.integration
def test_real_child_rejects_local_resolution_without_connecting():
    result = deliver('https://localhost/private?secret=not-logged', '{}', 'event-1')
    assert result == {'error': 'unsafe_destination', 'transient': False}


@pytest.mark.parametrize('address', ['fec0::1', '3fff::1'])
def test_special_ipv6_ranges_not_classified_by_old_python_tables(address):
    assert not public_address(address)


def test_surrogate_unicode_is_sanitized_validation_error():
    with pytest.raises(InvalidDestination):
        destination('https://example.com/\ud800')


def test_real_socket_informational_response_and_body_not_consumed():
    import socket
    from wepppy.rq.webhook_http import _read_response
    left, right = socket.socketpair()
    with left, right:
        right.sendall(b'HTTP/1.1 103 Early Hints\r\nLink: </style>\r\n\r\nHTTP/1.1 204 No Content\r\n\r\nBODY')
        assert _read_response(left)['status'] == 204
        assert left.recv(4) == b'BODY'
