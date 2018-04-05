# Copyright (c) 2016-2018, University of Idaho
# All rights reserved.
#
# Roger Lew (rogerlew.gmail.com)
#
# The project described was supported by NSF award number IIA-1301792
# from the NSF Idaho EPSCoR Program and by the National Science Foundation.

import numpy as np
import requests

step = 0.5
pad = 0.02

for lng in np.arange(-111.0, -66.25, step):
    for lat in np.arange(49, 24.75, -step):
        bbox = (lng - pad,
                lat - 0.5 - pad,
                lng + 0.5 + pad,
                lat + pad)

        query = 'https://sdmdataaccess.nrcs.usda.gov/Spatial/SDMWGS84Geographic.wfs?'\
                'SERVICE=WFS&VERSION=1.1.0&REQUEST=GetFeature&TYPENAME=MapunitPoly&'\
                'OUTPUTFORMAT=GML3&MAXFEATURES=25000&BBOX=%s' % (','.join(map(str, bbox)))

        fname = '201703_n%0.1f_w%0.1f_.gml' % (lat, abs(lng))
        print(query, fname)

        r = requests.get(query)

        if r.status_code == 200:
            fp = open(fname, 'w')
            fp.write(r.text)
            fp.close()



