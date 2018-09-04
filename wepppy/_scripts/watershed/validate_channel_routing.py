from os.path import join as _join
from os.path import split as _split
from os.path import exists as _exists

import numpy  as np

import matplotlib
from matplotlib import pyplot as plt

from osgeo import gdal, osr, ogr

gdal.UseExceptions()

from wepppy.all_your_base import read_tif, read_arc, isfloat
from wepppy.nodb import Ron, Topaz, Watershed


def subwta_cmap(topaz):
    s = str(int(topaz))

    if s.endswith('4'):
        return (0.0, 0.0, 1.0)

    if s == '0':
        return (1.0, 1.0, 1.0)

    else:
        np.random.seed(int(topaz))
        return np.random.rand(3, )


def read_topaz2wepp(fn):
    top2wepp = {}
    nhills = 0
    with open(fn) as fp:
        lines = fp.readlines()
        for line in lines:
            if 'Channels' in line:
                nhills = len(top2wepp)

            if line.startswith('#'):
                continue

            line = line.split()

            if len(line) == 3:
                top, wepp, area = line
                top, wepp = int(top), int(wepp) + nhills

                top2wepp[top] = wepp

    wepp2top = dict([(v, k) for k, v in top2wepp.items()])
    return top2wepp, wepp2top, nhills


def read_structure(fn, translator):
    _network = []
    chn = 1
    with open(fn) as fp:
        lines = fp.readlines()

        for line in lines:
            if line.startswith('2'):
                line = line.split('#')[0]
                line = line[1:]

                _network.append((translator.top(chn_enum=chn),
                                 [translator.top(wepp=int(v)) for v in line.split() if v != '0']))
                chn += 1

    return _network


if __name__ == "__main__":
    wd = '/geodata/weppcloud_runs/devvmec3-7b99-47f2-9e34-51e9f312e948'
    ron = Ron.getInstance(wd)
    topaz = Topaz.getInstance(wd)
    watershed = Watershed.getInstance(wd)

    translator = watershed.translator_factory()

    dem, transform, proj = read_tif(ron.dem_fn)
    dem = dem.T
    subwta, transform, proj = read_arc(topaz.subwta_arc)
    subwta = subwta.T
    subwta = np.array(subwta, dtype=np.int)


    lowhigh_coords = {}
    for top in translator:
        indx = np.where(subwta == top)

        mask = np.ones(subwta.shape, dtype=np.bool)
        mask[indx] = False

        _x = np.ma.array(dem, mask=mask)

        lowhigh_coords[top] = np.unravel_index(np.ma.argmin(_x), _x.shape)[::-1], \
                              np.unravel_index(np.ma.argmax(_x), _x.shape)[::-1]

    # network = read_network(NETWORK, nparser)
    network = read_structure(_join(ron.runs_dir, 'pw0.str'), translator)

    n, m = subwta.shape

    rbg_subwta = np.zeros((n, m, 3))
    for i in range(n):
        for j in range(m):
            rbg_subwta[i, j, :] = subwta_cmap(subwta[i, j])

    plt.Figure((20, 20))
    plt.imshow(rbg_subwta, cmap=None)

    for chn, links in network:
        print(chn, links)

        end_x, end_y = lowhigh_coords[chn][0]
        for top in links:
            if top == None:
                continue
            start_x, start_y = lowhigh_coords[top][1]
            dx, dy = end_x - start_x, end_y - start_y

            if str(top).endswith('4'):
                plt.arrow(start_x, start_y, dx, dy, head_width=2, head_length=2.5, fc='c', ec='c', alpha=0.5)
            else:
                plt.arrow(start_x, start_y, dx, dy, head_width=2, head_length=2.5, fc='m', ec='m', alpha=0.5)

    plt.savefig('weppcloud_channels.png', dpi=300)

