from os.path import split as _split
from os.path import join as _join
from os.path import exists as _exists
import os
import requests
from bs4 import BeautifulSoup
from urllib.request import urlopen


if __name__ == "__main__":
    measures = ['tmin', 'rad']
    for measure in measures:
        print(measure)
        url = 'http://rs-data1-mel.csiro.au/thredds/catalog/bawap/{}/month/catalog.html'.format(measure)
        file_server = 'http://rs-data1-mel.csiro.au/thredds/fileServer/'

        outdir = '/geodata/au/agdc/{}'.format(measure)
        if not _exists(outdir):
            os.mkdir(outdir)

        r = requests.get(url)

        soup = BeautifulSoup(r.text, 'html.parser')
        for link in soup.find_all('a'):
            href = link.attrs['href']
            if 'nc' not in href:
                continue

            href = href.replace('catalog.html?dataset=', file_server)

            fname = _split(href)[-1]
            fname = _join(outdir, fname)
            if not _exists(fname):
                print('fetching', href)
                output = urlopen(href)
                with open(fname, 'wb') as fp:
                    fp.write(output.read())

