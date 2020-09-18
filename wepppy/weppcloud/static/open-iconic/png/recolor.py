from glob import glob
from PIL import Image
import numpy as np

pngs = glob('*.png')

for png in pngs:
    if '-wh.png' in png:
        continue
    print(png)

    im = Image.open(png)
    print(im.format, im.size, im.mode)
    a = np.array(np.asarray(im))
    a[:, :, 0] += 255
    a[:, :, 1] += 255
    a[:, :, 2] += 255

    im2 = Image.fromarray(a)
    im2.save(png.replace('.png', '-wh.png'))
