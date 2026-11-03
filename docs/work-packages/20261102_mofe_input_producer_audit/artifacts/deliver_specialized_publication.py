"""Deliver only the independently approved revision-7 public attachment bytes."""
from pathlib import Path
import hashlib
import json
import urllib.request

NATIVE = Path('/home/workdir/wepp-forest-release-20261009/docs/release-notes/wepp_261029')
PUBLIC = Path('/home/workdir/wepppy/wepppy/weppcloud/static/reports/wepp/release-notes/wepp_261029')
EVIDENCE = Path('/wc1/holdouts/mipa-native-r7-20261103')
ENDPOINT = 'https://forest.tail305ec9.ts.net/weppcloud/static/reports/wepp/release-notes/wepp_261029/'
APPROVED = {
    'wepp_261029_release-notes-r7.pdf': ('build-r7/main-r7.pdf', '0cdd7c74ac7c2277a144e27d9a8053578eb6e63b6819b857bd45691b9fe69b3c', 'application/pdf'),
    'publication-manifest-r7.json': ('publication-manifest-r7.json', '7c7d80526573e08148590a5196dbd0ff4990d55426d0f16c25a5582e203ab1ac', 'application/json'),
}


def sha(data):
    return hashlib.sha256(data).hexdigest()


def main():
    earlier = {p.name: sha(p.read_bytes()) for p in PUBLIC.iterdir()
               if p.is_file() and p.name not in APPROVED}
    sources = {name: (NATIVE / values[0]).read_bytes() for name, values in APPROVED.items()}
    for name, content in sources.items():
        assert sha(content) == APPROVED[name][1], f'Approved source changed: {name}'
        destination = PUBLIC / name
        if destination.exists():
            assert destination.read_bytes() == content, f'Existing publication differs: {name}'
        else:
            with destination.open('xb') as stream:
                stream.write(content)
    receipt = {'passed': True, 'endpoint': ENDPOINT, 'deployment': False, 'attachments': {}}
    downloads = EVIDENCE / 'http-delivery-r7'
    downloads.mkdir(exist_ok=True)
    for name, (_, expected_hash, expected_type) in APPROVED.items():
        with urllib.request.urlopen(ENDPOINT + name, timeout=60) as response:
            data = response.read()
            status = response.status
            content_type = response.headers.get_content_type()
        (downloads / name).write_bytes(data)
        assert status == 200 and content_type == expected_type and sha(data) == expected_hash, name
        receipt['attachments'][name] = {'status': status, 'content_type': content_type,
                                        'sha256': sha(data), 'bytes': len(data)}
    assert all(sha((PUBLIC / name).read_bytes()) == value for name, value in earlier.items())
    receipt['preserved_earlier_public_files'] = earlier
    text = json.dumps(receipt, indent=2, sort_keys=True) + '\n'
    (NATIVE / 'evidence/delivery-receipt-r7.json').write_text(text)
    (EVIDENCE / 'delivery-receipt-r7.json').write_text(text)
    print(text)


if __name__ == '__main__':
    main()
