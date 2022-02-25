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
    parser.add_argument('--outdir', type=str, default='/home/mariana/BLKWD_UTR_300m', help='outdir for files')
    parser.add_argument('--input_csv', type=str, default='Blackwood_UTR_300m.csv', help='input file with RunID, WatershedName, Scenario colmans')

    args = parser.parse_args()

    prefix = args.prefix
    outdir = args.outdir
    input_csv = args.input_csv

    with open(input_csv) as fp:
        projects = [row for row in csv.DictReader(fp)]

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
