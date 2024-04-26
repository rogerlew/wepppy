import zipfile
from glob import glob
from os.path import split as _split

zip_fns = glob('*/*.zip')

for zip_fn in zip_fns:
    with zipfile.ZipFile(zip_fn, 'r') as zip_ref:
        zip_ref.extractall(_split(zip_fn)[0])

