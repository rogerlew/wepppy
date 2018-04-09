import os
from os.path import join as _join
from os.path import exists as _exists
import shutil
import json
from glob import glob

all_runs = '/geodata/weppcloud_runs/'

if __name__ == "__main__":
    fns = glob(_join(all_runs, '*/wepp.nodb'))
    for fn in fns:
        shutil.copyfile(fn, fn + '.old')
        with open(fn) as fp:
            js = json.load(fp)

        if 'status_log' in js:
            del js['status_log']

            with open(fn, 'w') as fp:
                print(fn)
                json.dump(js, fp)