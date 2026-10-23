"""Read the live local Usersum page, navigation and Roads-guide report link."""
from html.parser import HTMLParser
import json
from pathlib import Path
from urllib.parse import urljoin
import requests
from tests.roads.extract_fixture import digest


class Links(HTMLParser):
    def __init__(self):
        super().__init__()
        self.hrefs = []

    def handle_starttag(self, tag, attributes):
        if tag == 'a':
            self.hrefs.extend(value for name, value in attributes if name == 'href')


base = 'https://wc.bearhive.duckdns.org'
paths = {'report': '/weppcloud/usersum/doc/usersum.source.roads_validation',
         'navigation': '/weppcloud/usersum/', 'guide': '/weppcloud/usersum/doc/usersum.weppcloud.models.roads',
         'vendor': '/weppcloud/usersum/vendor/wepppy-roads/tests/roads/analysis_results_current.md'}
responses = {}
evidence = {}
for name, path in paths.items():
    response = requests.get(base + path, timeout=90)
    assert response.status_code == 200, (name, response.status_code, response.text[:100])
    responses[name] = response
    evidence[name] = {'status': response.status_code, 'url': response.url}
for name in ('report', 'vendor'):
    text = responses[name].text
    assert '<table>' in text and '516/516 profile cases completed' in text
    assert 'Four-texture comparison' in text and '1.17 million' in text
    assert 'whole-site unrutted success' in text
for name in ('navigation', 'guide'):
    links = Links()
    links.feed(responses[name].text)
    targets = [href for href in links.hrefs if 'roads_validation' in href or
               'wepppy-roads/tests/roads/analysis_results_current' in href]
    assert targets, name
    evidence[name]['report_links'] = targets
    for href in set(targets):
        linked = requests.get(urljoin(responses[name].url, href), timeout=90)
        assert linked.status_code == 200 and '516/516 profile cases completed' in linked.text, (name, href, linked.status_code, linked.url, linked.text[:100])
root = Path('/workdir/wepppy')
source = root / 'tests/roads/analysis_results_current.md'
vendor = root / 'wepppy/weppcloud/routes/usersum/vendor/wepppy-roads/tests/roads/analysis_results_current.md'
assert source.read_bytes() == vendor.read_bytes()
evidence['report_sha256'] = digest(source)
evidence['vendor_byte_identical'] = True
evidence['access'] = 'Live forest HTTPS through the normal reverse proxy; existing user-visible public documentation policy, no auth override'
output = Path(__file__).with_name('20261023_usersum_http_validation.json')
output.write_text(json.dumps(evidence, indent=2)+'\n')
print(json.dumps(evidence, indent=2))
