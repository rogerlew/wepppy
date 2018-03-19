import os
import shutil
from os.path import join as _join
from os.path import exists as _exists

import numpy as np
from numpy.testing import assert_array_equal

from wepppy.all_your_base import wmesque_retrieve, read_arc, read_tif


test_dir = 'wmesque_data'

if _exists(test_dir):
    shutil.rmtree(test_dir)

os.mkdir(test_dir)

nlcd_tif = _join(test_dir, 'nlcd.tif')
nlcd_asc = _join(test_dir, 'nlcd.asc')
ned_asc = _join(test_dir, 'ned.asc')


extent = [-120.234375, 38.9505984033, -120.05859375, 39.0871695498]
wmesque_retrieve('nlcd/2011', extent, nlcd_asc, 30.0)
wmesque_retrieve('nlcd/2011', extent, nlcd_tif, 30.0)
wmesque_retrieve('ned1/2016', extent, ned_asc, 30.0)

data, transform, proj = read_arc(nlcd_asc)
data2, transform2, proj2 = read_tif(nlcd_tif, dtype=np.int32)
data3, transform3, proj3 = read_arc(nlcd_asc, dtype=np.int32)

assert data.shape[0] == data2.shape[0], (data.shape, data2.shape)
assert data.shape[1] == data2.shape[1], (data.shape, data2.shape)

assert data.shape[0] == data3.shape[0], (data.shape, data3.shape)
assert data.shape[1] == data3.shape[1], (data.shape, data3.shape)

for v,v2 in zip(transform, transform2):
    assert v == v2
    
for v,v2 in zip(transform, transform3):
    assert v == v2
    
assert_array_equal(data, data2)