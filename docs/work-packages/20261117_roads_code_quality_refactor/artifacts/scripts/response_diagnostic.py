def pytest_exception_interact(node, call, report):
    for entry in call.excinfo.traceback:
        response = entry.frame.f_locals.get('response')
        if response is not None and hasattr(response, 'get_json'):
            print('ROADS_DIAGNOSTIC_RESPONSE', response.get_json())
