import shutil
import sys
import os
import argparse
import csv

from os.path import join as _join
from os.path import exists as _exists

from glob import glob

import subprocess
#from wepppy.all_your_base import ogrmerge
from wepppy.export import arc_export


if __name__ == "__main__":

    parser = argparse.ArgumentParser()
    parser.add_argument('--prefix', type=str, default='prefix', help='prefix for output files')
    parser.add_argument('--outdir', type=str, default='/home/mariana/BullRun_march_shp', help='outdir for files')
    parser.add_argument('--input_csv', type=str, default='BullRun_Runs_ID.csv', help='input file with RunID, WatershedName, Scenario colmans')

    args = parser.parse_args()

    prefix = args.prefix
    outdir = args.outdir
    input_csv = args.input_csv

    with open(input_csv) as fp:
        projects = [row for row in csv.DictReader(fp)]

    scenarios = set([project['Scenario'] for project in projects])

    if _exists(outdir):
        res = input(f'Outdir exists, Delete outdir: {outdir}?')
        if not res.lower().startswith('y'):
            sys.exit()

        shutil.rmtree(outdir)

    os.mkdir(outdir)

    for scenario in scenarios:

        channels = []
        subcatchments = []

        for project in projects:
            if project['Scenario'] != scenario:
                continue


            wd = _join('/geodata/weppcloud_runs/', project['RunID'])
            print(wd)

            chn = _join(wd, 'export', 'arcmap', 'channels.shp')

            if not _exists(chn):
                arc_export(wd)
            assert _exists(chn), chn
            channels.append(chn)

            sub = _join(wd, 'export', 'arcmap', 'subcatchments.shp')
            assert _exists(sub), sub
            subcatchments.append(sub)

        print(channels)
        print(sub)

        argv = ['python3', 'ogrmerge.py', '-o', _join(outdir, f'{prefix}_{scenario}_channels.shp'), '-single'] + channels
        print(argv)
        subprocess.call(argv)
        #ogrmerge.process(argv)

        argv = ['python3', 'ogrmerge.py', '-o', _join(outdir, f'{prefix}_{scenario}_subcatchments.shp'), '-single'] + subcatchments
        print(argv)
        subprocess.call(argv)

        #ogrmerge.process(argv)


        print('merged shps are in', outdir)
