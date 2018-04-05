import os
import sys
import csv
from urllib.request import urlretrieve
from zipfile import ZipFile

with open('ned936_20171221_153210.csv') as fp:
    reader = csv.DictReader(fp)
    for row in reader:
        url = row['downloadURL']
        fn = url.split('/')[-1]
        sys.stdout.write('{}... '.format(fn))
        assert fn.endswith('.zip')

        dest_dir = fn[:-4]
        if os.path.exists(dest_dir):
            sys.stdout.write('Skipping\n')
            continue

        urlretrieve(url, fn)
        with ZipFile(fn) as zf:
            zf.extractall(dest_dir)
        os.remove(fn)
        sys.stdout.write('Done\n')
