import tomli as tomllib
from glob import glob

cfgs = glob('*.cfg')

for cfg in cfgs:
    print(cfg)
    with open(cfg, 'rb') as f:
        cfg_dict = tomllib.load(f)
        print(cfg_dict)