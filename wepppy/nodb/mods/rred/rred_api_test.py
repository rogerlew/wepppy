from os.path import exists as _exists
from os.path import split as _split
from os.path import join as _join
import zipfile
import requests

from urllib.request import urlopen

from requests_toolbelt.multipart.encoder import MultipartEncoder


def send_request(sbs_fn, srid, class_low=2, class_mod=3, class_high=4):
    assert _exists(sbs_fn)

    fn = _split(sbs_fn)[-1]

    multipart_data = MultipartEncoder(
        fields={
                # file upload field
                'fileUpload': (fn,
                               open(sbs_fn, 'rb'),
                               'image/tiff'),
                # plain text fields
                'class_low': str(class_low),
                'class_mod': str(class_mod),
                'class_high': str(class_high),
                'srid': srid,
               }
        )

    response = requests.post('https://geodjango.mtri.org/baer/geowepp/supplied/maps/',
                             data=multipart_data,
                             headers={'Content-Type': multipart_data.content_type})

    assert response.status_code == 200
    return response.json()


def retrieve_rred(key, out_dir='./', extract=True):
    url = 'https://geodjango.mtri.org/baer/geowepp/package.asc?burned=true&simplify=false&scale=30&key={key}' \
          .format(key=key)

    output = urlopen(url)
    archive_path = _join(out_dir, 'DisturbedWepp_KEY-%s.zip' % key)
    with open(archive_path, 'wb') as fp:
        fp.write(output.read())

    if extract:
        with zipfile.ZipFile(archive_path) as zf:
            zf.extractall(out_dir)


if __name__ == '__main__':
    rred_proj = send_request('/home/weppdev/Desktop/Emerald_sbs.tif')
    print(rred_proj)
    retrieve_rred(rred_proj['key'])
