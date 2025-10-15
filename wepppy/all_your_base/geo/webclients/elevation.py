import requests


def elevationquery(lng, lat):
    url = 'https://wepp.cloud/webservices/elevationquery'
    r = requests.post(url, json=dict(lat=lat, lng=lng))

    if r.status_code != 200:
        raise Exception("Encountered error retrieving from elevationquery")

    # noinspection PyBroadException
    try:
        _json = r.json()
    except Exception:
        _json = None

    if _json is None:
        raise Exception("Cannot parse json from elevation response")

    return _json['Elevation']
