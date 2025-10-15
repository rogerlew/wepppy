from urllib.request import urlopen
from urllib.error import HTTPError, URLError
import json, shutil, socket
import json
import base64
from deprecated import deprecated

def isfloat(x):
    try:
        float(x)
    except:
        return False
    return True

TIMEOUT = 300
WMESQUE_ENDPOINT = 'https://wepp.cloud/webservices/wmesque/'
WMESQUE2_ENDPOINT = 'https://wepp.cloud/webservices/wmesque2/'

@deprecated
def _wmesque1_retrieve(dataset, extent, fname, cellsize, resample=None):
    global WMESQUE_ENDPOINT

    assert isfloat(cellsize)

    assert all([isfloat(v) for v in extent])
    assert len(extent) == 4

    extent = ','.join([str(v) for v in extent])

    if fname.lower().endswith('.tif'):
        fmt = 'GTiff'

    elif fname.lower().endswith('.asc'):
        fmt = 'AAIGrid'

    elif fname.lower().endswith('.png'):
        fmt = 'PNG'

    else:
        raise ValueError('fname must end with .tif, .asc, or .png')

    url = f'{WMESQUE_ENDPOINT}{dataset}/?bbox={extent}&cellsize={cellsize}&format={fmt}'

    if resample is not None:
        url += f'&resample={resample}'

    try:
        output = urlopen(url, timeout=60)
        with open(fname, 'wb') as fp:
            fp.write(output.read())
    except Exception:
        raise Exception("Error retrieving: %s" % url)

    return 1

def _b64url_to_bytes(s: str) -> bytes:
    # add '=' padding for urlsafe b64
    pad = '=' * ((4 - len(s) % 4) % 4)
    return base64.urlsafe_b64decode(s + pad)


def wmesque_retrieve(
        dataset, 
        extent, 
        fname, 
        cellsize, 
        resample=None, 
        v=1,
        write_meta=True,
        wmesque_endpoint=None):
    v = int(v)

    if v == 1:
        return _wmesque1_retrieve(dataset, extent, fname, cellsize, resample)
    
    global WMESQUE_ENDPOINT

    assert isfloat(cellsize)

    assert all([isfloat(v) for v in extent])
    assert len(extent) == 4

    if wmesque_endpoint is None:
        wmesque_endpoint = WMESQUE2_ENDPOINT

    if wmesque_endpoint.endswith('/'):
        wmesque_endpoint = wmesque_endpoint[:-1]

    extent = ','.join([str(v) for v in extent])

    if fname.lower().endswith('.tif'):
        fmt = 'GTiff'

    elif fname.lower().endswith('.asc'):
        fmt = 'AAIGrid'

    elif fname.lower().endswith('.png'):
        fmt = 'PNG'

    else:
        raise ValueError('fname must end with .tif, .asc, or .png')

    url = f'{wmesque_endpoint}/retrieve/{dataset}/?bbox={extent}&cellsize={cellsize}&format={fmt}'

    if resample is not None:
        url += f'&resample={resample}'

    meta = {
        'wmesque_retrieve': {
            'url': url,
            'wmesque_endpoint': wmesque_endpoint
        }
    }

    try:
        with urlopen(url, timeout=TIMEOUT) as resp:
            status = getattr(resp, "status", resp.getcode())
            if not (200 <= status < 300):
                payload = resp.read()  # bytes; safe to read once
                text = payload.decode("utf-8", "replace")
                raise RuntimeError(f"Unexpected HTTP {status} for {url}: {text}")

            # headers are available without consuming the body
            hdrs = resp.headers
            #from pprint import pprint
            #pprint(hdrs.items())
            meta_b64 = hdrs.get("WMesque-Meta")
            if meta_b64:
                try:
                    meta.update(json.loads(_b64url_to_bytes(meta_b64).decode("utf-8")))
                except Exception as e:
                    meta.update({"_meta_header_decode_error": str(e), "_raw": meta_b64})

            # stream body to file
            with open(fname, "wb") as fp:
                shutil.copyfileobj(resp, fp)

            if write_meta:
                with open(f'{fname}.meta', 'w') as fp:
                    json.dump(meta, fp, indent=2)
                
            return 1

    except HTTPError as e:
        # HTTP errors still have headers and a readable body
        payload = e.read() or b""
        text = payload.decode("utf-8", "replace")
        ct = (e.headers or {}).get("Content-Type", "")
        try:
            err_json = json.loads(text) if "json" in ct or text.strip().startswith("{") else None
        except Exception:
            err_json = None
        details = f" body={err_json}" if err_json is not None else f" body={text[:2000]}"
        raise RuntimeError(f"HTTPError {e.code} {e.reason} for {e.url};{details}") from e

    except (URLError, socket.timeout) as e:
        # DNS failures, timeouts, refused connections, etc.
        raise RuntimeError(f"Network error fetching {url}: {getattr(e, 'reason', e)}") from e

if __name__ == "__main__":
    from pprint import pprint
    pprint(wmesque_retrieve('nlcd/2019',
                     [-116.42555236816408, 45.233799855252855, -116.32701873779298, 45.303146403608935],
                     '/home/roger/output.tif',
                     30.0,
                     v=2,
                     wmesque_endpoint='https://wmesque2.bearhive.duckdns.org'))