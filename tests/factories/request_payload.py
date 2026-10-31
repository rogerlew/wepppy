"""Exercise registered Flask payload consumers without bypassing route wrappers."""
import inspect
import re


def assert_malformed_routes(client, runid, config, tmp_path):
    tested = []
    for rule in client.application.url_map.iter_rules():
        if 'POST' not in rule.methods or '/runs/' not in rule.rule:
            continue
        view = inspect.unwrap(client.application.view_functions[rule.endpoint])
        source = inspect.getsource(view)
        if not any(parser in source for parser in ('parse_request_payload(', 'parse_json_payload(')):
            continue
        def parameter(match):
            return runid if match[1] == 'runid' else config if match[1] == 'config' else 'test'
        path = re.sub(r'<(?:[^:>]+:)?([^>]+)>', parameter, rule.rule)
        before = {p.relative_to(tmp_path): p.read_bytes() for p in tmp_path.rglob('*.nodb')}
        response = client.post(path, data='{', content_type='application/json')
        assert response.status_code == 400, (path, response.get_data(as_text=True))
        assert response.json['error']['code'] == 'invalid_request', (path, response.json)
        assert {p.relative_to(tmp_path): p.read_bytes() for p in tmp_path.rglob('*.nodb')} == before
        tested.append(path)
    assert tested
    print('Covered malformed Flask routes:', tested)
