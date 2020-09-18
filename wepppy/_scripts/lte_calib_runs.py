import os
import sys

from copy import deepcopy

import shutil
from os.path import exists as _exists
from pprint import pprint
from time import time
from time import sleep
from datetime import datetime

import wepppy
from wepppy.nodb import *
from os.path import join as _join
from wepppy.wepp.out import TotalWatSed
from wepppy.export import arc_export

from osgeo import gdal, osr
gdal.UseExceptions()


def all_hillslopes(landuse, soils):
    return list(landuse.domlc_d.keys())


def _identify_outcrop_mukeys(soils):
    outcrop_mukeys = []
    _soils = soils.subs_summary
    for top in _soils:
        desc = _soils[top]['desc'].lower()
        if 'melody-rock outcrop' in desc or 'ellispeak-rock outcrop' in desc:
            mukey = str(_soils[top]['mukey'])
            outcrop_mukeys.append(mukey)

    return outcrop_mukeys


def not_shrub_and_not_outcrop_selector(landuse, soils):
    domlc_d = landuse.domlc_d
    domsoil_d = soils.domsoil_d
    outcrop_mukeys = _identify_outcrop_mukeys(soils)

    topaz_ids = []
    for top in domsoil_d:
        if str(domsoil_d[top]) not in outcrop_mukeys and domlc_d[top] != '104':
            topaz_ids.append(top)

    return topaz_ids


def shrub_and_not_outcrop_selector(landuse, soils):
    domlc_d = landuse.domlc_d
    domsoil_d = soils.domsoil_d
    outcrop_mukeys = _identify_outcrop_mukeys(soils)

    topaz_ids = []
    for top in domsoil_d:
        if str(domsoil_d[top]) not in outcrop_mukeys and domlc_d[top] == '104':
            topaz_ids.append(top)

    return topaz_ids


def not_shrub_selector(landuse, soils):
    domlc_d = landuse.domlc_d
    topaz_ids = []
    for top in domlc_d:
        if str(domlc_d[top]) != '104':
            topaz_ids.append(top)

    return topaz_ids


def shrub_selector(landuse, soils):
    domlc_d = landuse.domlc_d
    topaz_ids = []
    for top in domlc_d:
        if domlc_d[top] == '104':
            topaz_ids.append(top)

    return topaz_ids


def outcrop_selector(landuse, soils):
    domsoil_d = soils.domsoil_d
    outcrop_mukeys = _identify_outcrop_mukeys(soils)

    topaz_ids = []
    for top in domsoil_d:
        if domsoil_d[top] in outcrop_mukeys:
            topaz_ids.append(top)

    return topaz_ids


def not_outcrop_selector(landuse, soils):
    domsoil_d = soils.domsoil_d
    outcrop_mukeys = _identify_outcrop_mukeys(soils)

    topaz_ids = []
    for top in domsoil_d:
        if domsoil_d[top] not in outcrop_mukeys:
            topaz_ids.append(top)

    return topaz_ids

wd = None
def log_print(msg):
    now = datetime.now()
    print('[{now}] {wd}: {msg}'.format(now=now, wd=wd, msg=msg))

if __name__ == '__main__':

    watersheds = [
        dict(wd='Watershed_1',  # 150 ha
             extent=[-120.1619338989258, 39.14763521827571, -119.92160797119142, 39.33376633431887],
             map_center=[-120.04177093505861, 39.2407625100131],
             map_zoom=12,
             outlet=[-120.09622790374877, 39.20593567273984],
             landuse=None,
             cs=50, erod=0.000001),
        dict(wd='Watershed_2',  # 190 ha
             extent=[-120.1619338989258, 39.14763521827571, -119.92160797119142, 39.33376633431887],
             map_center=[-120.04177093505861, 39.2407625100131],
             map_zoom=12,
             outlet=[-120.09007219506651, 39.211997939797904],
             landuse=None,
             cs=50, erod=0.000001),
        dict(wd='Watershed_3',  # 610 ha
             extent=[-120.1619338989258, 39.14763521827571, -119.92160797119142, 39.33376633431887],
             map_center=[-120.04177093505861, 39.2407625100131],
             map_zoom=12,
             outlet=[-120.08804679389792, 39.218974048542954],
             landuse=None,
             cs=50, erod=0.000001),
        dict(wd='Watershed_4',  # 210 ha
             extent=[-120.1619338989258, 39.14763521827571, -119.92160797119142, 39.33376633431887],
             map_center=[-120.04177093505861, 39.2407625100131],
             map_zoom=12,
             outlet=[-120.08641274873328, 39.22487886998101],
             landuse=None,
             cs=50, erod=0.000001),
        dict(wd='Watershed_5',  # 23 ha
             extent=[-120.1619338989258, 39.14763521827571, -119.92160797119142, 39.33376633431887],
             map_center=[-120.04177093505861, 39.2407625100131],
             map_zoom=12,
             outlet=[-120.08933580988858, 39.22981668179069],
             landuse=None,
             cs=50, erod=0.000001),
        dict(wd='Watershed_6',  # 46 ha
             extent=[-120.1619338989258, 39.14763521827571, -119.92160797119142, 39.33376633431887],
             map_center=[-120.04177093505861, 39.2407625100131],
             map_zoom=12,
             outlet=[-120.08356881159119, 39.226429198412944],
             landuse=None,
             cs=50, erod=0.000001),
        dict(wd='Watershed_7',  # 770 ha
             extent=[-120.1619338989258, 39.14763521827571, -119.92160797119142, 39.33376633431887],
             map_center=[-120.04177093505861, 39.2407625100131],
             map_zoom=12,
             outlet=[-120.07969459253908, 39.22768334903354],
             landuse=None,
             cs=50, erod=0.000001),
        dict(wd='Watershed_8',  # 80 ha
             extent=[-120.1619338989258, 39.14763521827571, -119.92160797119142, 39.33376633431887],
             map_center=[-120.04177093505861, 39.2407625100131],
             map_zoom=12,
             outlet=[-120.05797912271075, 39.24010882250784],
             landuse=None,
             cs=50, erod=0.000001),
        dict(wd='Watershed_9',  # 1200 ha
             extent=[-120.1619338989258, 39.14763521827571, -119.92160797119142, 39.33376633431887],
             map_center=[-120.04177093505861, 39.2407625100131],
             map_zoom=12,
             outlet=[-120.0396132899316, 39.23883229646565],
             landuse=None,
             cs=50, erod=0.000001),
        dict(wd='Watershed_10',  # 1100 ha
             extent=[-120.1619338989258, 39.14763521827571, -119.92160797119142, 39.33376633431887],
             map_center=[-120.04177093505861, 39.2407625100131],
             map_zoom=12,
             outlet=[-120.03057579150752, 39.238872298828994],
             landuse=None,
             cs=50, erod=0.000001),
        dict(wd='Watershed_11',  # 76 ha
             extent=[-120.1619338989258, 39.14763521827571, -119.92160797119142, 39.33376633431887],
             map_center=[-120.04177093505861, 39.2407625100131],
             map_zoom=12,
             outlet=[-120.02654678811952, 39.2355263472678],
             landuse=None,
             cs=50, erod=0.000001),
        dict(wd='Watershed_12',  # 160 ha
             extent=[-120.1619338989258, 39.14763521827571, -119.92160797119142, 39.33376633431887],
             map_center=[-120.04177093505861, 39.2407625100131],
             map_zoom=12,
             outlet=[-120.02345678903843, 39.23463658610686],
             landuse=None,
             cs=50, erod=0.000001),
        dict(wd='Watershed_13',  # 370 ha
             extent=[-120.1619338989258, 39.14763521827571, -119.92160797119142, 39.33376633431887],
             map_center=[-120.04177093505861, 39.2407625100131],
             map_zoom=12,
             outlet=[-119.99814918521255, 39.225068116460506],
             landuse=None,
             cs=50, erod=0.000001),
        dict(wd='Watershed_14',  # 450 ha
             extent=[-120.1619338989258, 39.14763521827571, -119.92160797119142, 39.33376633431887],
             map_center=[-120.04177093505861, 39.2407625100131],
             map_zoom=12,
             outlet=[-119.98883774006968, 39.24779919914662],
             landuse=None,
             cs=50, erod=0.000001),
        dict(wd='Watershed_15',  # 400 ha
             extent=[-120.1619338989258, 39.14763521827571, -119.92160797119142, 39.33376633431887],
             map_center=[-120.04177093505861, 39.2407625100131],
             map_zoom=12,
             outlet=[-119.97838738323198, 39.248339060781475],
             landuse=None,
             cs=50, erod=0.000001),
        dict(wd='Watershed_16',  # 92 ha
             extent=[-120.1619338989258, 39.14763521827571, -119.92160797119142, 39.33376633431887],
             map_center=[-120.04177093505861, 39.2407625100131],
             map_zoom=12,
             outlet=[-119.97179085084468, 39.24816757762806],
             landuse=None,
             cs=50, erod=0.000001),
        dict(wd='Watershed_17',  # 490 ha
             extent=[-120.1619338989258, 39.14763521827571, -119.92160797119142, 39.33376633431887],
             map_center=[-120.04177093505861, 39.2407625100131],
             map_zoom=12,
             outlet=[-119.95707223120424, 39.24291905726153],
             landuse=None,
             cs=50, erod=0.000001),
        dict(wd='Watershed_18_Third',  # 1600 ha
             extent=[-120.04760742187501, 39.16839998800286, -119.80728149414064, 39.35447606884594],
             map_center=[-119.92744445800783, 39.261499771230774],
             map_zoom=12,
             outlet=[-119.94713185797971, 39.239460705991355],
             landuse=None,
             cs=50, erod=0.000001),
        dict(wd='Watershed_19_Incline',  # 1700 ha
             extent=[-120.04760742187501, 39.16839998800286, -119.80728149414064, 39.35447606884594],
             map_center=[-119.92744445800783, 39.261499771230774],
             map_zoom=12,
             outlet=[-119.94500218172628, 39.2404858227834],
             landuse=None,
             cs=50, erod=0.000001),
        dict(wd='Watershed_20',  # 500 ha
             extent=[-120.04760742187501, 39.16839998800286, -119.80728149414064, 39.35447606884594],
             map_center=[-119.92744445800783, 39.261499771230774],
             map_zoom=12,
             outlet=[-119.93519389103228, 39.234282368305905],
             landuse=None,
             cs=50, erod=0.000001),
        dict(wd='Watershed_21',  # 310 ha
             extent=[-120.04760742187501, 39.16839998800286, -119.80728149414064, 39.35447606884594],
             map_center=[-119.92744445800783, 39.261499771230774],
             map_zoom=12,
             outlet=[-119.92772893484674, 39.22219445266412],
             landuse=None,
             cs=50, erod=0.000001),
        dict(wd='Watershed_22',  # 230 ha
             extent=[-120.04760742187501, 39.16839998800286, -119.80728149414064, 39.35447606884594],
             map_center=[-119.92744445800783, 39.261499771230774],
             map_zoom=12,
             outlet=[-119.92780585626933, 39.21246741121267],
             landuse=None,
             cs=50, erod=0.000001),
        dict(wd='Watershed_23',  # 52 ha
             extent=[-120.04760742187501, 39.16839998800286, -119.80728149414064, 39.35447606884594],
             map_center=[-119.92744445800783, 39.261499771230774],
             map_zoom=12,
             outlet=[-119.92902337136051, 39.208445758549246],
             landuse=None,
             cs=50, erod=0.000001),
        dict(wd='Watershed_24',  # 25 ha
             extent=[-120.04760742187501, 39.16839998800286, -119.80728149414064, 39.35447606884594],
             map_center=[-119.92744445800783, 39.261499771230774],
             map_zoom=12,
             outlet=[-119.93014075643508, 39.19874614288978],
             landuse=None,
             cs=50, erod=0.000001),
        dict(wd='Watershed_25',  # 33 ha
             extent=[-120.04760742187501, 39.16839998800286, -119.80728149414064, 39.35447606884594],
             map_center=[-119.92744445800783, 39.261499771230774],
             map_zoom=12,
             outlet=[-119.92712434849918, 39.19623427594098],
             landuse=None,
             cs=50, erod=0.000001),
        dict(wd='Watershed_26',  # 140 ha
             extent=[-120.04760742187501, 39.16839998800286, -119.80728149414064, 39.35447606884594],
             map_center=[-119.92744445800783, 39.261499771230774],
             map_zoom=12,
             outlet=[-119.92704812670831, 39.190016450091775],
             landuse=None,
             cs=50, erod=0.000001),
        dict(wd='Watershed_27',  # 1300 ha
             extent=[-120.01396179199219, 39.019450429324046, -119.77363586425783, 39.20592074849823],
             map_center=[-119.89379882812501, 39.11274726579313],
             map_zoom=12,
             outlet=[-119.93270185597697, 39.16542835468725],
             landuse=None,
             cs=50, erod=0.000001),
        dict(wd='Watershed_28',  # 51 ha
             extent=[-120.01396179199219, 39.019450429324046, -119.77363586425783, 39.20592074849823],
             map_center=[-119.89379882812501, 39.11274726579313],
             map_zoom=12,
             outlet=[-119.93090374225022, 39.150834255220026],
             landuse=None,
             cs=50, erod=0.000001),
        dict(wd='Watershed_29',  # 510 ha
             extent=[-120.01396179199219, 39.019450429324046, -119.77363586425783, 39.20592074849823],
             map_center=[-119.89379882812501, 39.11274726579313],
             map_zoom=12,
             outlet=[-119.93136079483678, 39.148367001968865],
             landuse=None,
             cs=50, erod=0.000001),
        dict(wd='Watershed_30',  # 140 ha
             extent=[-120.01396179199219, 39.019450429324046, -119.77363586425783, 39.20592074849823],
             map_center=[-119.89379882812501, 39.11274726579313],
             map_zoom=12,
             outlet=[-119.93642518249555, 39.143635771481485],
             landuse=None,
             cs=50, erod=0.000001),
        dict(wd='Watershed_31',  # 40 ha
             extent=[-120.01396179199219, 39.019450429324046, -119.77363586425783, 39.20592074849823],
             map_center=[-119.89379882812501, 39.11274726579313],
             map_zoom=12,
             outlet=[-119.94066697186948, 39.14185550725643],
             landuse=None,
             cs=50, erod=0.000001),
        dict(wd='Watershed_32',  # 1600 ha
             extent=[-120.01396179199219, 39.019450429324046, -119.77363586425783, 39.20592074849823],
             map_center=[-119.89379882812501, 39.11274726579313],
             map_zoom=12,
             outlet=[-119.94656529513026, 39.1017421575381],
             landuse=None,
             cs=50, erod=0.000001),
        dict(wd='Watershed_33',  # 88 ha
             extent=[-120.01396179199219, 39.019450429324046, -119.77363586425783, 39.20592074849823],
             map_center=[-119.89379882812501, 39.11274726579313],
             map_zoom=12,
             outlet=[-119.9418433230724, 39.09864545553091],
             landuse=None,
             cs=50, erod=0.000001),
        dict(wd='Watershed_34',  # 99 ha
             extent=[-120.01396179199219, 39.019450429324046, -119.77363586425783, 39.20592074849823],
             map_center=[-119.89379882812501, 39.11274726579313],
             map_zoom=12,
             outlet=[-119.94062104067505, 39.09482976550799],
             landuse=None,
             cs=50, erod=0.000001),
        dict(wd='Watershed_35',  # 1100 ha
             extent=[-120.01396179199219, 39.019450429324046, -119.77363586425783, 39.20592074849823],
             map_center=[-119.89379882812501, 39.11274726579313],
             map_zoom=12,
             outlet=[-119.93987372418106, 39.08805371534803],
             landuse=None,
             cs=50, erod=0.000001),
        dict(wd='Watershed_36',  # 290 ha
             extent=[-120.01396179199219, 39.019450429324046, -119.77363586425783, 39.20592074849823],
             map_center=[-119.89379882812501, 39.11274726579313],
             map_zoom=12,
             outlet=[-119.94139490719957, 39.068905396563665],
             landuse=None,
             cs=50, erod=0.000001),
        dict(wd='Watershed_37',  # 550 ha
             extent=[-120.01396179199219, 39.019450429324046, -119.77363586425783, 39.20592074849823],
             map_center=[-119.89379882812501, 39.11274726579313],
             map_zoom=12,
             outlet=[-119.94044934750968, 39.06671850835026],
             landuse=None,
             cs=50, erod=0.000001),
        dict(wd='Watershed_38',  # 31 ha
             extent=[-120.01396179199219, 39.019450429324046, -119.77363586425783, 39.20592074849823],
             map_center=[-119.89379882812501, 39.11274726579313],
             map_zoom=12,
             outlet=[-119.94319963374946, 39.05922347741282],
             landuse=None,
             cs=50, erod=0.000001),
        dict(wd='Watershed_39',  # 36 ha
             extent=[-120.01396179199219, 39.019450429324046, -119.77363586425783, 39.20592074849823],
             map_center=[-119.89379882812501, 39.11274726579313],
             map_zoom=12,
             outlet=[-119.9445062251884, 39.05304180979089],
             landuse=None,
             cs=50, erod=0.000001),
        dict(wd='Watershed_40',  # 150 ha
             extent=[-120.01396179199219, 39.019450429324046, -119.77363586425783, 39.20592074849823],
             map_center=[-119.89379882812501, 39.11274726579313],
             map_zoom=12,
             outlet=[-119.94636531738409, 39.05011770248522],
             landuse=None,
             cs=50, erod=0.000001),
        dict(wd='Watershed_41',  # 700 ha
             extent=[-120.01396179199219, 39.019450429324046, -119.77363586425783, 39.20592074849823],
             map_center=[-119.89379882812501, 39.11274726579313],
             map_zoom=12,
             outlet=[-119.94819197052668, 39.039895724271986],
             landuse=None,
             cs=50, erod=0.000001),
        dict(wd='Watershed_42',  # 680 ha
             extent=[-120.06202697753908, 38.87045372777545, -119.8217010498047, 39.05731715424236],
             map_center=[-119.94186401367189, 38.963947050281696],
             map_zoom=12,
             outlet=[-119.94876901553465, 39.01494787512556],
             landuse=None,
             cs=50, erod=0.000001),
        dict(wd='Watershed_43',  # 430 ha
             extent=[-120.06202697753908, 38.87045372777545, -119.8217010498047, 39.05731715424236],
             map_center=[-119.94186401367189, 38.963947050281696],
             map_zoom=12,
             outlet=[-119.94804448075419, 39.007631888060544],
             landuse=None,
             cs=50, erod=0.000001),
        dict(wd='Watershed_44',  # 940 ha
             extent=[-120.06202697753908, 38.87045372777545, -119.8217010498047, 39.05731715424236],
             map_center=[-119.94186401367189, 38.963947050281696],
             map_zoom=12,
             outlet=[-119.95345634105546, 38.99453069976447],
             landuse=None,
             cs=50, erod=0.000001),
        dict(wd='Watershed_45',  # 1200 ha
             extent=[-120.06202697753908, 38.87045372777545, -119.8217010498047, 39.05731715424236],
             map_center=[-119.94186401367189, 38.963947050281696],
             map_zoom=12,
             outlet=[-119.94974779877337, 38.97605598069683],
             landuse=None,
             cs=50, erod=0.000001),
        dict(wd='Watershed_46_Edgewood',  # 1700 ha
             extent=[-120.06202697753908, 38.87045372777545, -119.8217010498047, 39.05731715424236],
             map_center=[-119.94186401367189, 38.963947050281696],
             map_zoom=12,
             outlet=[-119.94974968108744, 38.96794819106319],
             landuse=None,
             cs=50, erod=0.000001),
        dict(wd='Watershed_47',  # 490 ha
             extent=[-120.06202697753908, 38.87045372777545, -119.8217010498047, 39.05731715424236],
             map_center=[-119.94186401367189, 38.963947050281696],
             map_zoom=12,
             outlet=[-119.95773966719415, 38.95113043297326],
             landuse=None,
             cs=50, erod=0.000001),
        dict(wd='Watershed_48',  # 310 ha
             extent=[-120.06202697753908, 38.87045372777545, -119.8217010498047, 39.05731715424236],
             map_center=[-119.94186401367189, 38.963947050281696],
             map_zoom=12,
             outlet=[-119.96022900417523, 38.949573776843714],
             landuse=None,
             cs=50, erod=0.000001),
        dict(wd='Watershed_49',  # 510 ha
             extent=[-120.06202697753908, 38.87045372777545, -119.8217010498047, 39.05731715424236],
             map_center=[-119.94186401367189, 38.963947050281696],
             map_zoom=12,
             outlet=[-119.96519583350171, 38.94673025403238],
             landuse=None,
             cs=50, erod=0.000001),
        dict(wd='Watershed_50_Trout',  # 11000 ha
             extent=[-120.22338867187501, 38.65012583524745, -119.74273681640626, 39.02451827974919],
             map_center=[-119.98306274414064, 38.83756825896614],
             map_zoom=11,
             outlet=[-119.99412900886539, 38.940182494695605],
             landuse=None,
             cs=50, erod=0.000001),
        dict(wd='Watershed_51_SLT',  # 14000 ha
             extent=[-120.22338867187501, 38.65012583524745, -119.74273681640626, 39.02451827974919],
             map_center=[-119.98306274414064, 38.83756825896614],
             map_zoom=11,
             outlet=[-120.00218219772862, 38.937957400165246],
             landuse=None,
             cs=50, erod=0.000001,
             csa=10),
        dict(wd='Watershed_52',  # 5700 ha
             extent=[-120.22338867187501, 38.65012583524745, -119.74273681640626, 39.02451827974919],
             map_center=[-119.98306274414064, 38.83756825896614],
             map_zoom=11,
             outlet=[-120.05848479974783, 38.940472140058006],
             landuse=None,
             cs=50, erod=0.000001)

    ]

    scenarios = [
               # dict(wd='SimFire.2020.ki5krcs.chn_12_fccsFuels_obs_cli',
               #      landuse=None,
               #      cfg='lt-fire'),
               # dict(wd='SimFire.2020.ki5krcs.chn_12_landisFuels_obs_cli',
               #      landuse=None,
               #      cfg='lt-fire-future'),
               # dict(wd='SimFire.2020.ki5krcs.chn_12_landisFuels_fut_cli_A2',
               #      landuse=None,
               #      cfg='lt-fire-future',
               #      climate='future'),
               dict(wd='CurCond.2020.cl532.vanilla.ki5krcs',
                    landuse=None,
                    climate_mode='vanilla'),
               # dict(wd='PrescFireS.2020.ki5krcs.chn_12',
               #      landuse=[(not_shrub_selector, 110), (shrub_selector, 122)]),
               # dict(wd='LowSevS.2020.ki5krcs.chn_12',
               #      landuse=[(not_shrub_selector, 106), (shrub_selector, 121)]),
               # dict(wd='ModSevS.2020.ki5krcs.chn_12',
               #      landuse=[(not_shrub_selector, 118), (shrub_selector, 120)]),
               # dict(wd='HighSevS.2020.ki5krcs.chn_12',
               #      landuse=[(not_shrub_selector, 105), (shrub_selector, 119)]),
               # dict(wd='Thinn96.2020.ki5krcs.chn_12',
               #      landuse=[(not_shrub_selector, 123)]),
               # dict(wd='Thinn93.2020.ki5krcs.chn_12',
               #      landuse=[(not_shrub_selector, 115)]),
               # dict(wd='Thinn85.2020.ki5krcs.chn_12',
               #      landuse=[(not_shrub_selector, 117)]),
               # dict(wd='Thinn75.2020.kikrcs.chn_12',
               #      landuse=[(not_shrub_selector, 124)]),
               # dict(wd='LowSev4.3.2b.2',
               #      landuse=[(not_shrub_selector, 106)]),
               # dict(wd='LowSev4.4.2b.2',
               #      landuse=[(not_shrub_and_not_outcrop_selector, 106),
               #               (shrub_and_not_outcrop_selector, 121)]),
               # dict(wd='LowSev4.5.2b.2',
               #      landuse=[(not_shrub_and_not_outcrop_selector, 106)]),
               # dict(wd='ModSev4.3.2b.2',
               #      landuse=[(not_shrub_selector, 118)]),
               # dict(wd='ModSev4.4.2b.2',
               #      landuse=[(not_shrub_and_not_outcrop_selector, 118),
               #               (shrub_and_not_outcrop_selector, 120)]),
               # dict(wd='ModSev4.5.2b.2',
               #      landuse=[(not_shrub_and_not_outcrop_selector, 118)]),
               # dict(wd='HighSev4.3.2b.2',
               #      landuse=[(not_shrub_selector, 105)]),
               # dict(wd='HighSev4.4.2b.2',
               #      landuse=[(not_shrub_and_not_outcrop_selector, 105),
               #               (shrub_and_not_outcrop_selector, 119)]),
               # dict(wd='HighSev4.5.2b.2',
               #      landuse=[(not_shrub_and_not_outcrop_selector, 105)]),
                ]

    projects = []

    wc = sys.argv[-1]
    if '.py' in wc:
        wc = None

    for scenario in scenarios:
        for watershed in watersheds:
            projects.append(deepcopy(watershed))
            projects[-1]['cfg'] = scenario.get('cfg', 'lt')
            projects[-1]['landuse'] = scenario['landuse']
            projects[-1]['climate'] = scenario.get('climate', 'observed')
            projects[-1]['wd'] = 'lte_%s_%s' % (watershed['wd'], scenario['wd'])

    failed = open('failed', 'w')
    for proj in projects:
        try:
            wd = proj['wd']
            extent = proj['extent']
            map_center = proj['map_center']
            map_zoom = proj['map_zoom']
            outlet = proj['outlet']
            default_landuse = proj['landuse']
            cfg = proj['cfg']
            climate_mode = proj['climate']
            csa = proj.get('csa', 5)

            if wc is not None:
                if not wc in wd:
                    continue

            log_print('cleaning dir')
            if _exists(wd):
                print()
                shutil.rmtree(wd)
            os.mkdir(wd)

            log_print('initializing project')
            ron = Ron(wd, "%s.cfg" % cfg)
            ron.name = wd
            ron.set_map(extent, map_center, zoom=map_zoom)

            log_print('fetching dem')
            ron.fetch_dem()

            log_print('building channels')
            topaz = Topaz.getInstance(wd)
            topaz.build_channels(csa=csa, mcl=60)
            topaz.set_outlet(*outlet)
            sleep(0.5)

            log_print('building subcatchments')
            topaz.build_subcatchments()

            log_print('abstracting watershed')
            wat = Watershed.getInstance(wd)
            wat.abstract_watershed(cell_width=None)
            translator = wat.translator_factory()
            topaz_ids = [top.split('_')[1] for top in translator.iter_sub_ids()]

            log_print('building landuse')
            landuse = Landuse.getInstance(wd)
            landuse.mode = LanduseMode.Gridded
            landuse.build()
            landuse = Landuse.getInstance(wd)

            # 105 - Tahoe High severity fire
            # topaz_ids is a list of string ids e.g. ['22', '23']
            if default_landuse is not None:
                log_print('setting default landuse')

                tops = []

                for selector, dom in default_landuse:
                    _topaz_ids = selector(landuse, soils)
                    landuse.modify(_topaz_ids, dom)
                    tops.extend(_topaz_ids)
                #
                # # all_hillslopes
                # if '.2_Watershed' in wd:
                #     assert '1251' in tops, default_landuse
                #     assert '1752' in tops
                #     assert '1222' in tops
                #     assert '2203' in tops
                #
                # # not shrub
                # elif '.3_Watershed' in wd:
                #     assert '1251' in tops
                #     assert '1752' not in tops
                #     assert '1222' in tops
                #     assert '2203' not in tops
                #
                # # not outcrop
                # elif '.4_Watershed' in wd:
                #     assert '1251' in tops
                #     assert '1752' in tops
                #     assert '1222' not in tops
                #     assert '2203' not in tops
                #
                # # not shrub or not outcrop
                # elif '.5_Watershed' in wd:
                #     assert '1251' in tops
                #     assert '1752' not in tops
                #     assert '1222' not in tops
                #     assert '2203' not in tops

            log_print('building soils')
            soils = Soils.getInstance(wd)
            soils.mode = SoilsMode.Gridded
            soils.build()

            log_print('building climate')

            if climate_mode == 'observed':
                climate = Climate.getInstance(wd)
                stations = climate.find_closest_stations()
                climate.input_years = 27
                climate.climatestation = stations[0]['id']

                climate.climate_mode = ClimateMode.Observed
                climate.climate_spatialmode = ClimateSpatialMode.Multiple
                climate.set_observed_pars(start_year=1990, end_year=2016)
            elif climate_mode == 'future':
                climate = Climate.getInstance(wd)
                stations = climate.find_closest_stations()
                climate.input_years = 27
                climate.climatestation = stations[0]['id']

                climate.climate_mode = ClimateMode.Future
                climate.climate_spatialmode = ClimateSpatialMode.Single
                climate.set_future_pars(start_year=2018, end_year=2018+27)
            elif climate_mode == 'vanilla':
                climate = Climate.getInstance(wd)
                stations = climate.find_closest_stations()
                climate.input_years = 30
                climate.climatestation = stations[0]['id']

                climate.climate_mode = ClimateMode.Vanilla
                climate.climate_spatialmode = ClimateSpatialMode.Single
                #climate.set_orig_cli_fn(_join(climate._future_clis_wc, 'Ward_Creek_A2.cli'))
            else:
                raise Exception("Unknown climate_mode")

            climate.build(verbose=1)

            log_print('prepping wepp')
            wepp = Wepp.getInstance(wd)
            wepp.prep_hillslopes()

            log_print('running hillslopes')
            wepp.run_hillslopes()

            log_print('prepping watershed')
            wepp = Wepp.getInstance(wd)
            wepp.prep_watershed(erodibility=proj['erod'], critical_shear=proj['cs'])

            log_print('running watershed')
            wepp.run_watershed()

            log_print('generating loss report')
            loss_report = wepp.report_loss()

            log_print('generating totalwatsed report')
            fn = _join(ron.export_dir, 'totalwatsed.csv')

            totwatsed = TotalWatSed(_join(ron.output_dir, 'totalwatsed.txt'),
                                    wepp.baseflow_opts, wepp.phosphorus_opts)
            totwatsed.export(fn)
            assert _exists(fn)

            log_print('exporting arcmap resources')
            arc_export(wd)
        except:
            failed.write('%s\n' % wd)
            raise
