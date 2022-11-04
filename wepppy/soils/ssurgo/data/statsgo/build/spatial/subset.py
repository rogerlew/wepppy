from subprocess import Popen
import math

rasterxsize = 66029
rasterysize = 35683

n = 6003

for i in range(math.ceil(rasterxsize/n)):
    for j in range(math.ceil(rasterysize/n)):
        xoff = i * n
        yoff = j * n
        xsize = n
        if xoff + n > rasterxsize:
            xsize = rasterxsize - xoff

        ysize = n
        if yoff + n > rasterysize:
            ysize = rasterysize - yoff

        dst_fn = f'_mukeys_{i:02}_{j:02}.tif'

        cmd = ['gdal_translate', '-srcwin', xoff, yoff, xsize, ysize, '.vrt', dst_fn]
        print(cmd)

        cmd = [str(arg) for arg in cmd]
        p = Popen(cmd)
        p.wait()

