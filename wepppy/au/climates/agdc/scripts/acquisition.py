"""Fetch AGDC monthly NetCDF files into the local geodata cache.

The script mirrors the CSIRO THREDDS layout locally so downstream processing can
run offline.  Each measure (``tmin``, ``tmax``, ``rain``, ``rad``) receives its
own directory under ``/geodata/au/agdc/<measure>`` populated with the monthly
NetCDF slices.
"""

from __future__ import annotations

from collections.abc import Sequence
from os.path import exists as _exists
from os.path import join as _join
from os.path import split as _split
import os
from urllib.request import urlopen

import requests
from bs4 import BeautifulSoup

DEFAULT_MEASURES: tuple[str, ...] = ('tmin', 'tmax', 'rain', 'rad')


def download_agdc_monthlies(measures: Sequence[str] | None = None) -> None:
    """Download the AGDC NetCDF monthly stacks for each climate variable.

    Args:
        measures: Collection of measure names to download. Defaults to
            ``DEFAULT_MEASURES``.

    The downloader is intentionally lightweight—it scrapes the THREDDS catalog
    page for ``.nc`` links and streams each file directly to disk.  Re-running
    the function is idempotent; existing files are skipped so operators can
    resume interrupted transfers.
    """

    selected = list(measures) if measures is not None else list(DEFAULT_MEASURES)

    for measure in selected:
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


if __name__ == "__main__":
    download_agdc_monthlies()
