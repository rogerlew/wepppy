from glob import glob
from wepppy.wepp.management import read_management
man_fns = glob('*.man')

for man_fn in man_fns:
    man = read_management(man_fn)
    man.dump_to_json(f'{man_fn}.json')
