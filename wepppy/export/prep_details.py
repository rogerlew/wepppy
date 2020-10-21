from os.path import join as _join
from os.path import exists as _exists
import os
import csv
from wepppy.nodb import Ron


def export_hillslopes_prep_details(wd):
    ron = Ron.getInstance(wd)
    subcatchments_summary = ron.subs_summary()
    
    fieldnames = ('topaz_id', 'wepp_id', 'width', 'length', 'area', 'slope', 'aspect',
                  'dom_landuse', 'dom_soil', 'cli_fn', 'longest_fp', 'longest_fp_length', 'longest_fp_slope')

    out_dir = _join(ron.export_dir, 'prep_details')
    
    if not _exists(out_dir):
        os.mkdir(out_dir)
        
    fp = open(_join(out_dir, 'hillslopes.csv'), 'w')
    
    wtr = csv.DictWriter(fp, fieldnames)
    wtr.writeheader()
    wtr.writerow(dict(topaz_id='', wepp_id='', width='m', length='m', area='ha', slope='decimal', aspect='degree',
                      dom_landuse='', dom_soil='', cli_fn='',
                      longest_fp='', longest_fp_length='m', longest_fp_slope='decimal'))

    for d in subcatchments_summary:
        try:
            topaz_id = d['meta']['topaz_id']
        except KeyError:
            topaz_id = None

        try:
            wepp_id = d['meta']['wepp_id']
        except KeyError:
            wepp_id = None

        try:
            width = d['watershed']['width']
        except KeyError:
            width = None

        try:
            length = d['watershed']['length']
        except KeyError:
            length = None

        try:
            area = d['watershed']['area']
            area *= 0.0001
        except KeyError:
            area = None

        try:
            slope = d['watershed']['slope_scalar']
        except KeyError:
            slope = None

        try:
            aspect = d['watershed']['aspect']
        except KeyError:
            aspect = None

        try:
            dom_landuse = d['landuse']['key']
        except KeyError:
            dom_landuse = None

        try:
            dom_soil = d['soil']['mukey']
        except KeyError:
            dom_soil = None

        try:
            cli_fn = d['climate']['cli_fn']
        except KeyError:
            cli_fn = None

        try:
            longest_fp = d['watershed']['fp_longest']
        except KeyError:
            longest_fp = None

        try:
            longest_fp_length = d['watershed']['fp_longest_length']
        except KeyError:
            longest_fp_length = None

        try:
            longest_fp_slope = d['watershed']['fp_longest_slope']
        except KeyError:
            longest_fp_slope = None

        wtr.writerow(dict(topaz_id=topaz_id, wepp_id=wepp_id,
                          width=width, length=length,
                          area=area, slope=slope, aspect=aspect,
                          dom_landuse=dom_landuse, dom_soil=dom_soil, cli_fn=cli_fn,
                          longest_fp=longest_fp,
                          longest_fp_length=longest_fp_length,
                          longest_fp_slope=longest_fp_slope))

    fp.close()


def export_channels_prep_details(wd):
    ron = Ron.getInstance(wd)
    chns_summary = ron.chns_summary()
    fieldnames = ('topaz_id', 'wepp_id', 'chn_enum', 'chn_wepp_width', 'order', 'length', 'area', 'slope', 'aspect',
                  'channel_type', 'dom_soil', 'cli_fn')

    out_dir = _join(ron.export_dir, 'prep_details')

    if not _exists(out_dir):
        os.mkdir(out_dir)

    fp = open(_join(out_dir, 'channels.csv'), 'w')

    wtr = csv.DictWriter(fp, fieldnames)
    wtr.writeheader()
    wtr.writerow(dict(topaz_id='', wepp_id='', chn_enum='', chn_wepp_width='m', order='', length='m', area='ha',
                      slope='decimal', aspect='degree',
                      channel_type='', dom_soil='', cli_fn=''))

    for d in chns_summary:
        try:
            topaz_id = d['meta']['topaz_id']
        except KeyError:
            topaz_id = None

        try:
            wepp_id = d['meta']['wepp_id']
        except KeyError:
            wepp_id = None

        try:
            chn_enum = d['meta']['wepp_id']
        except KeyError:
            chn_enum = None

        try:
            chn_wepp_width = d['watershed']['chn_wepp_width']
        except KeyError:
            chn_wepp_width = None

        try:
            length = d['watershed']['length']
        except KeyError:
            length = None

        try:
            order = d['watershed']['order']
        except KeyError:
            order = None

        try:
            area = d['watershed']['area']
            area *= 0.0001
        except KeyError:
            area = None

        try:
            slope = d['watershed']['slope_scalar']
        except KeyError:
            slope = None

        try:
            aspect = d['watershed']['aspect']
        except KeyError:
            aspect = None

        try:
            channel_type = d['watershed']['channel_type']
        except KeyError:
            channel_type = None

        try:
            dom_soil = d['soil']['mukey']
        except KeyError:
            dom_soil = None

        try:
            cli_fn = d['climate']['cli_fn']
        except KeyError:
            cli_fn = None

        wtr.writerow(dict(topaz_id=topaz_id, wepp_id=wepp_id, chn_enum=chn_enum, order=order,
                          chn_wepp_width=chn_wepp_width, length=length,
                          area=area, slope=slope, aspect=aspect,
                          channel_type=channel_type, dom_soil=dom_soil, cli_fn=cli_fn))

    fp.close()
