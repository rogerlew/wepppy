import os

from os.path import exists as _exists
from os.path import join as _join
from os.path import split as _split
import csv

import sys
import shutil
from glob import glob
from wepppy.nodb import Ron, Wepp
from wepppy.wepp.stats import HillSummary, ChannelSummary, OutletSummary, SedimentDelivery

import argparse

#os.chdir('/geodata/weppcloud_runs/')

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--prefix', type=str, default='prefix', help='prefix for output files')
    parser.add_argument('--outdir', type=str, default='/home/mariana/BullRun_march', 
                        help='outdir for files')
    parser.add_argument('--input_csv', type=str, default='BullRun_Runs_ID.csv', 
                        help='input file with RunID, WatershedName, Scenario colmans')
    parser.add_argument('--test', default=False, action="store_true", 
                        help='test whether projects exist without running')

    args = parser.parse_args()

    prefix = args.prefix
    outdir = args.outdir
    input_csv = args.input_csv
    test = args.test

    with open(input_csv) as fp:
        projects = [row for row in csv.DictReader(fp)]

    if test:
        for i, project in enumerate(projects):
            run_id = project['RunID']
    
            nodb_fn = _join('/geodata/weppcloud_runs/', run_id, 'ron.nodb')
            if not _exists(nodb_fn):
                print(f'project "{run_id}" is not valid or doesn\'t exist')
        sys.exit()


    if _exists(outdir):
        res = input(f'Outdir exists, Delete outdir: {outdir}?')
        if not res.lower().startswith('y'):
            sys.exit()

        shutil.rmtree(outdir)

    os.mkdir(outdir)

    fp_hill = open(_join(outdir, '%s_hill_summary.csv' % prefix), 'w')
    fp_chn = open(_join(outdir, '%s_chn_summary.csv' % prefix), 'w')
    fp_out = open(_join(outdir, '%s_out_summary.csv' % prefix), 'w')
    fp_sd = open(_join(outdir, '%s_sed_del_summary.csv' % prefix), 'w')

    for i, project in enumerate(projects):
        wd = _join('/geodata/weppcloud_runs/', project['RunID'])
        scenario = project['Scenario']
        watershed = project['WatershedName']

        assert _exists(wd), wd

        if not os.path.isdir(wd):
            continue

        print(wd)
        write_header = i == 0
        ron = Ron.getInstance(wd)
        subcatchments_summary = {_d['meta']['topaz_id']: _d for _d in ron.subs_summary()}
        channels_summary = {_d['meta']['topaz_id']: _d for _d in ron.chns_summary()}

        name = ron.name

        run_descriptors = [('ProjectName', name), ('Scenario', scenario), ('Watershed', watershed)]

        loss = Wepp.getInstance(wd).report_loss()

        hill_rpt = HillSummary(loss, class_fractions=True, fraction_under=0.016, subs_summary=subcatchments_summary)

        chn_rpt = ChannelSummary(loss, chns_summary=channels_summary)
        out_rpt = OutletSummary(loss, fraction_under=0.016)
        sed_del = SedimentDelivery(wd)

        hill_rpt.write(fp_hill, write_header=write_header, run_descriptors=run_descriptors)
        chn_rpt.write(fp_chn, write_header=write_header, run_descriptors=run_descriptors)
        out_rpt.write(fp_out, write_header=write_header, run_descriptors=run_descriptors)
        sed_del.write(fp_sd, write_header=write_header, run_descriptors=run_descriptors)

    fp_hill.close()
    fp_chn.close()
    fp_out.close()
    fp_sd.close()
