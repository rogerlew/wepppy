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
from wepppy.nodb import (
    Ron, Topaz, Watershed, Landuse, Soils, Climate, Wepp, SoilsMode, ClimateMode, ClimateSpatialMode, LanduseMode
)
from wepppy.nodb.mods.locations import LakeTahoe

from os.path import join as _join
from wepppy.nodb.mods.locations.lt.selectors import *
from wepppy.wepp.out import TotalWatSed
from wepppy.export import arc_export

from osgeo import gdal, osr

gdal.UseExceptions()

wd = None


def log_print(msg):
    global wd

    now = datetime.now()
    print('[{now}] {wd}: {msg}'.format(now=now, wd=wd, msg=msg))


if __name__ == '__main__':

    os.chdir('/geodata/weppcloud_runs/')

    watersheds = [
        dict(watershed='0_Near_Burton_Creek',  # Watershed_6
             extent=[-120.25222778320314, 39.102091011833686, -120.01190185546876, 39.28834275351453],
             map_center=[-120.13206481933595, 39.19527859633793],
             map_zoom=12,
             outlet=[-120.14460408169862, 39.17224134827233],
             landuse=None,
             cs=30, erod=0.000001,
             surf_runoff=0.003, lateral_flow=0.004, baseflow=0.005, sediment=1100.0,
             gwstorage=100, bfcoeff=0.04, dscoeff=0.00, bfthreshold=1.001,
             mid_season_crop_coeff=0.95, p_coeff=0.8),
        dict(watershed='1_Unnamed_Creek_at_Tahoe_City_State_Park',  # Watershed_5
             extent=[-120.25222778320314, 39.102091011833686, -120.01190185546876, 39.28834275351453],
             map_center=[-120.13206481933595, 39.19527859633793],
             map_zoom=12,
             outlet=[-120.1402884859731, 39.175919130374645],
             landuse=None,
             cs=30, erod=0.000001,
             surf_runoff=0.003, lateral_flow=0.004, baseflow=0.005, sediment=1100.0,
             gwstorage=100, bfcoeff=0.04, dscoeff=0.00, bfthreshold=1.001,
             mid_season_crop_coeff=0.95, p_coeff=0.8),
        dict(watershed='2_Burton_Creek',  # Watershed_4
             extent=[-120.20605087280275, 39.15083019711799, -120.08588790893556, 39.243953257043124],
             map_center=[-120.14596939086915, 39.19740715574304],
             map_zoom=13,
             outlet=[-120.12241504431637, 39.181379503672105],
             # outlet=[-120.1233, 39.1816],  # [-120.12241504431637, 39.181379503672105],
             landuse=None,
             cs=30, erod=0.000001,
             surf_runoff=0.003, lateral_flow=0.004, baseflow=0.005, sediment=1100.0,
             gwstorage=100, bfcoeff=0.04, dscoeff=0.00, bfthreshold=1.001,
             mid_season_crop_coeff=0.95, p_coeff=0.8),
        dict(watershed='3_Unnamed_Creek_near_Lake_Forest',  # Watershed_3
             extent=[-120.25497436523439, 39.072244930479926, -120.0146484375, 39.25857565711887],
             map_center=[-120.1348114013672, 39.165471994238374],
             map_zoom=12,
             outlet=[-120.12165282292143, 39.18644160172608],
             landuse=None,
             cs=30, erod=0.000001,
             surf_runoff=0.003, lateral_flow=0.004, baseflow=0.005, sediment=1100.0,
             gwstorage=100, bfcoeff=0.04, dscoeff=0.00, bfthreshold=1.001,
             mid_season_crop_coeff=0.95, p_coeff=0.8),
        dict(watershed='4_Unnamed_Creek_at_Lake_Forest',  # Watershed_2
             extent=[-120.25497436523439, 39.072244930479926, -120.0146484375, 39.25857565711887],
             map_center=[-120.1348114013672, 39.165471994238374],
             map_zoom=12,
             outlet=[-120.11460381632118, 39.18896973503106],
             landuse=None,
             cs=30, erod=0.000001,
             surf_runoff=0.003, lateral_flow=0.004, baseflow=0.005, sediment=1100.0,
             gwstorage=100, bfcoeff=0.04, dscoeff=0.00, bfthreshold=1.001,
             mid_season_crop_coeff=0.95, p_coeff=0.8),
        dict(watershed='5_Dollar_Creek',  # Watershed_1
             extent=[-120.25497436523439, 39.072244930479926, -120.0146484375, 39.25857565711887],
             map_center=[-120.1348114013672, 39.165471994238374],
             map_zoom=12,
             outlet=[-120.09757304843217, 39.19773527084747],
             landuse=None,
             cs=30, erod=0.000001,
             surf_runoff=0.003, lateral_flow=0.004, baseflow=0.005, sediment=1100.0,
             gwstorage=100, bfcoeff=0.04, dscoeff=0.00, bfthreshold=1.001,
             mid_season_crop_coeff=0.95, p_coeff=0.8),
        dict(watershed='6_Unnamed_Creek_at_Cedar_Flat',  # 150 ha  Watershed_1
             extent=[-120.1619338989258, 39.14763521827571, -119.92160797119142, 39.33376633431887],
             map_center=[-120.04177093505861, 39.2407625100131],
             map_zoom=12,
             outlet=[-120.09622790374877, 39.20593567273984],
             landuse=None,
             cs=30, erod=0.000001,
             surf_runoff=0.003, lateral_flow=0.004, baseflow=0.005, sediment=1100.0,
             gwstorage=100, bfcoeff=0.04, dscoeff=0.00, bfthreshold=1.001,
             mid_season_crop_coeff=0.95, p_coeff=0.8),
        dict(watershed='6_Intervening_Area_Cedar_Flat',  # 190 ha  Watershed_2
             extent=[-120.1619338989258, 39.14763521827571, -119.92160797119142, 39.33376633431887],
             map_center=[-120.04177093505861, 39.2407625100131],
             map_zoom=12,
             outlet=[-120.09007219506651, 39.211997939797904],
             landuse=None,
             cs=30, erod=0.000001,
             surf_runoff=0.003, lateral_flow=0.004, baseflow=0.005, sediment=1100.0,
             gwstorage=100, bfcoeff=0.04, dscoeff=0.00, bfthreshold=1.001,
             mid_season_crop_coeff=0.95, p_coeff=0.8),
        dict(watershed='7_Watson_Creek',  # 610 ha  Watershed_3
             extent=[-120.1619338989258, 39.14763521827571, -119.92160797119142, 39.33376633431887],
             map_center=[-120.04177093505861, 39.2407625100131],
             map_zoom=12,
             outlet=[-120.08804679389792, 39.218974048542954],
             landuse=None,
             cs=30, erod=0.000001,
             surf_runoff=0.003, lateral_flow=0.004, baseflow=0.005, sediment=1100.0,
             gwstorage=100, bfcoeff=0.04, dscoeff=0.00, bfthreshold=1.001,
             mid_season_crop_coeff=0.95, p_coeff=0.8),
        dict(watershed='8_Carnelian_Bay_Creek',  # 210 ha  Watershed_4
             extent=[-120.1619338989258, 39.14763521827571, -119.92160797119142, 39.33376633431887],
             map_center=[-120.04177093505861, 39.2407625100131],
             map_zoom=12,
             outlet=[-120.08641274873328, 39.22487886998101],
             landuse=None,
             cs=30, erod=0.000001,
             surf_runoff=0.003, lateral_flow=0.004, baseflow=0.005, sediment=1100.0,
             gwstorage=100, bfcoeff=0.04, dscoeff=0.00, bfthreshold=1.001,
             mid_season_crop_coeff=0.95, p_coeff=0.8),
        dict(watershed='9_Intervening_Area_Carnelian_Bay_1',  # 23 ha  Watershed_5
             extent=[-120.1619338989258, 39.14763521827571, -119.92160797119142, 39.33376633431887],
             map_center=[-120.04177093505861, 39.2407625100131],
             map_zoom=12,
             outlet=[-120.08933580988858, 39.22981668179069],
             landuse=None,
             cs=30, erod=0.000001,
             surf_runoff=0.003, lateral_flow=0.004, baseflow=0.005, sediment=1100.0,
             gwstorage=100, bfcoeff=0.04, dscoeff=0.00, bfthreshold=1.001,
             mid_season_crop_coeff=0.95, p_coeff=0.8),
        dict(watershed='9_Intervening_Area_Carnelian_Bay_2',  # 46 ha  Watershed_6
             extent=[-120.1619338989258, 39.14763521827571, -119.92160797119142, 39.33376633431887],
             map_center=[-120.04177093505861, 39.2407625100131],
             map_zoom=12,
             outlet=[-120.08356881159119, 39.226429198412944],
             landuse=None,
             cs=30, erod=0.000001,
             surf_runoff=0.003, lateral_flow=0.004, baseflow=0.005, sediment=1100.0,
             gwstorage=100, bfcoeff=0.04, dscoeff=0.00, bfthreshold=1.001,
             mid_season_crop_coeff=0.95, p_coeff=0.8),
        dict(watershed='9_Carnelian_Creek',  # 770 ha  Watershed_7
             extent=[-120.1619338989258, 39.14763521827571, -119.92160797119142, 39.33376633431887],
             map_center=[-120.04177093505861, 39.2407625100131],
             map_zoom=12,
             outlet=[-120.07969459253908, 39.22768334903354],
             landuse=None,
             cs=30, erod=0.000001,
             surf_runoff=0.003, lateral_flow=0.004, baseflow=0.005, sediment=1100.0,
             gwstorage=100, bfcoeff=0.04, dscoeff=0.00, bfthreshold=1.001,
             mid_season_crop_coeff=0.95, p_coeff=0.8),
        dict(watershed='10_Intervening_Area_Agate_Bay',  # 80 ha  Watershed_8
             extent=[-120.1619338989258, 39.14763521827571, -119.92160797119142, 39.33376633431887],
             map_center=[-120.04177093505861, 39.2407625100131],
             map_zoom=12,
             outlet=[-120.05797912271075, 39.24010882250784],
             landuse=None,
             cs=30, erod=0.000001,
             surf_runoff=0.003, lateral_flow=0.004, baseflow=0.005, sediment=1100.0,
             gwstorage=100, bfcoeff=0.04, dscoeff=0.00, bfthreshold=1.001,
             mid_season_crop_coeff=0.95, p_coeff=0.8),
        dict(watershed='10_Snow_Creek',  # 1200 ha  Watershed_9
             extent=[-120.1619338989258, 39.14763521827571, -119.92160797119142, 39.33376633431887],
             map_center=[-120.04177093505861, 39.2407625100131],
             map_zoom=12,
             outlet=[-120.0396132899316, 39.23883229646565],
             landuse=None,
             cs=30, erod=0.000001,
             surf_runoff=0.003, lateral_flow=0.004, baseflow=0.005, sediment=1100.0,
             gwstorage=100, bfcoeff=0.04, dscoeff=0.00, bfthreshold=1.001,
             mid_season_crop_coeff=0.95, p_coeff=0.8),
        dict(watershed='11_Griff_Creek',  # 1100 ha  Watershed_10
             extent=[-120.1619338989258, 39.14763521827571, -119.92160797119142, 39.33376633431887],
             map_center=[-120.04177093505861, 39.2407625100131],
             map_zoom=12,
             outlet=[-120.03057579150752, 39.238872298828994],
             landuse=None,
             cs=30, erod=0.000001,
             surf_runoff=0.003, lateral_flow=0.004, baseflow=0.005, sediment=1100.0,
             gwstorage=100, bfcoeff=0.04, dscoeff=0.00, bfthreshold=1.001,
             mid_season_crop_coeff=0.95, p_coeff=0.8),
        dict(watershed='12_Intervening_Area_Griff_to_Baldy',  # 76 ha  Watershed_11
             extent=[-120.1619338989258, 39.14763521827571, -119.92160797119142, 39.33376633431887],
             map_center=[-120.04177093505861, 39.2407625100131],
             map_zoom=12,
             outlet=[-120.02654678811952, 39.2355263472678],
             landuse=None,
             cs=30, erod=0.000001,
             surf_runoff=0.003, lateral_flow=0.004, baseflow=0.005, sediment=1100.0,
             gwstorage=100, bfcoeff=0.04, dscoeff=0.00, bfthreshold=1.001,
             mid_season_crop_coeff=0.95, p_coeff=0.8),
        dict(watershed='12_Baldy_Creek',  # 160 ha  Watershed_12
             extent=[-120.1619338989258, 39.14763521827571, -119.92160797119142, 39.33376633431887],
             map_center=[-120.04177093505861, 39.2407625100131],
             map_zoom=12,
             outlet=[-120.02345678903843, 39.23463658610686],
             landuse=None,
             cs=30, erod=0.000001,
             surf_runoff=0.003, lateral_flow=0.004, baseflow=0.005, sediment=1100.0,
             gwstorage=100, bfcoeff=0.04, dscoeff=0.00, bfthreshold=1.001,
             mid_season_crop_coeff=0.95, p_coeff=0.8),
        dict(watershed='13_East_Stateline_Point',  # 370 ha Watershed_13
             extent=[-120.1619338989258, 39.14763521827571, -119.92160797119142, 39.33376633431887],
             map_center=[-120.04177093505861, 39.2407625100131],
             map_zoom=12,
             outlet=[-119.99814918521255, 39.225068116460506],
             landuse=None,
             cs=30, erod=0.000001,
             surf_runoff=0.003, lateral_flow=0.004, baseflow=0.005, sediment=1100.0,
             gwstorage=100, bfcoeff=0.04, dscoeff=0.00, bfthreshold=1.001,
             mid_season_crop_coeff=0.95, p_coeff=0.8),
        dict(watershed='14_First_Creek',  # 450 ha  Watershed_14
             extent=[-120.1619338989258, 39.14763521827571, -119.92160797119142, 39.33376633431887],
             map_center=[-120.04177093505861, 39.2407625100131],
             map_zoom=12,
             outlet=[-119.98883774006968, 39.24779919914662],
             landuse=None,
             cs=30, erod=0.000001,
             surf_runoff=0.003, lateral_flow=0.004, baseflow=0.005, sediment=1100.0,
             gwstorage=100, bfcoeff=0.04, dscoeff=0.00, bfthreshold=1.001,
             mid_season_crop_coeff=0.95, p_coeff=0.8),
        dict(watershed='15_Second_Creek',  # 400 ha  Watershed_15
             extent=[-120.1619338989258, 39.14763521827571, -119.92160797119142, 39.33376633431887],
             map_center=[-120.04177093505861, 39.2407625100131],
             map_zoom=12,
             outlet=[-119.97838738323198, 39.248339060781475],
             landuse=None,
             cs=30, erod=0.000001,
             surf_runoff=0.003, lateral_flow=0.004, baseflow=0.005, sediment=1100.0,
             gwstorage=100, bfcoeff=0.04, dscoeff=0.00, bfthreshold=1.001,
             mid_season_crop_coeff=0.95, p_coeff=0.8),
        dict(watershed='16_Intervening_Area_Second_to_Wood',  # 92 ha  Watershed_16
             extent=[-120.1619338989258, 39.14763521827571, -119.92160797119142, 39.33376633431887],
             map_center=[-120.04177093505861, 39.2407625100131],
             map_zoom=12,
             outlet=[-119.97179085084468, 39.24816757762806],
             landuse=None,
             cs=30, erod=0.000001,
             surf_runoff=0.003, lateral_flow=0.004, baseflow=0.005, sediment=1100.0,
             gwstorage=100, bfcoeff=0.04, dscoeff=0.00, bfthreshold=1.001,
             mid_season_crop_coeff=0.95, p_coeff=0.8),
        dict(watershed='17_Wood_Creek',  # 490 ha Watershed_17
             extent=[-120.1619338989258, 39.14763521827571, -119.92160797119142, 39.33376633431887],
             map_center=[-120.04177093505861, 39.2407625100131],
             map_zoom=12,
             outlet=[-119.95707223120424, 39.24291905726153],
             landuse=None,
             cs=30, erod=0.000001,
             surf_runoff=0.003, lateral_flow=0.004, baseflow=0.005, sediment=1100.0,
             gwstorage=100, bfcoeff=0.04, dscoeff=0.00, bfthreshold=1.001,
             mid_season_crop_coeff=0.95, p_coeff=0.8),
        dict(watershed='18_Third_Creek',  # 1600 ha  Watershed_18_Third
             extent=[-120.04760742187501, 39.16839998800286, -119.80728149414064, 39.35447606884594],
             map_center=[-119.92744445800783, 39.261499771230774],
             map_zoom=12,
             outlet=[-119.94713185797971, 39.239460705991355],
             landuse=None,
             cs=30, erod=0.000001,
             surf_runoff=0.003, lateral_flow=0.004, baseflow=0.005, sediment=1100.0,
             gwstorage=100, bfcoeff=0.04, dscoeff=0.00, bfthreshold=1.001,
             mid_season_crop_coeff=0.95, p_coeff=0.8),
        dict(watershed='19_Incline_Creek',  # 1700 ha  Watershed_19_Incline
             extent=[-120.04760742187501, 39.16839998800286, -119.80728149414064, 39.35447606884594],
             map_center=[-119.92744445800783, 39.261499771230774],
             map_zoom=12,
             outlet=[-119.94500218172628, 39.2404858227834],
             landuse=None,
             cs=30, erod=0.000001,
             surf_runoff=0.003, lateral_flow=0.004, baseflow=0.005, sediment=1100.0,
             gwstorage=100, bfcoeff=0.04, dscoeff=0.00, bfthreshold=1.001,
             mid_season_crop_coeff=0.95, p_coeff=0.8),
        dict(watershed='20_Mill_Creek',  # 500 ha  Watershed_20
             extent=[-120.04760742187501, 39.16839998800286, -119.80728149414064, 39.35447606884594],
             map_center=[-119.92744445800783, 39.261499771230774],
             map_zoom=12,
             outlet=[-119.93519389103228, 39.234282368305905],
             landuse=None,
             cs=30, erod=0.000001,
             surf_runoff=0.003, lateral_flow=0.004, baseflow=0.005, sediment=1100.0,
             gwstorage=100, bfcoeff=0.04, dscoeff=0.00, bfthreshold=1.001,
             mid_season_crop_coeff=0.95, p_coeff=0.8),
        dict(watershed='21_Tunnel_Creek',  # 310 ha Watershed_21
             extent=[-120.04760742187501, 39.16839998800286, -119.80728149414064, 39.35447606884594],
             map_center=[-119.92744445800783, 39.261499771230774],
             map_zoom=12,
             outlet=[-119.92772893484674, 39.22219445266412],
             landuse=None,
             cs=30, erod=0.000001,
             surf_runoff=0.003, lateral_flow=0.004, baseflow=0.005, sediment=1100.0,
             gwstorage=100, bfcoeff=0.04, dscoeff=0.00, bfthreshold=1.001,
             mid_season_crop_coeff=0.95, p_coeff=0.8),
        dict(watershed='22_Unnamed_creek_at_Sand_Harbor',  # 230 ha  Watershed_22
             extent=[-120.04760742187501, 39.16839998800286, -119.80728149414064, 39.35447606884594],
             map_center=[-119.92744445800783, 39.261499771230774],
             map_zoom=12,
             outlet=[-119.92780585626933, 39.21246741121267],
             landuse=None,
             cs=30, erod=0.000001,
             surf_runoff=0.003, lateral_flow=0.004, baseflow=0.005, sediment=1100.0,
             gwstorage=100, bfcoeff=0.04, dscoeff=0.00, bfthreshold=1.001,
             mid_season_crop_coeff=0.95, p_coeff=0.8),
        dict(watershed='23_Intervening_Area_Sand_Harbor_1',  # 52 ha  Watershed_23
             extent=[-120.04760742187501, 39.16839998800286, -119.80728149414064, 39.35447606884594],
             map_center=[-119.92744445800783, 39.261499771230774],
             map_zoom=12,
             outlet=[-119.92902337136051, 39.208445758549246],
             landuse=None,
             cs=30, erod=0.000001,
             surf_runoff=0.003, lateral_flow=0.004, baseflow=0.005, sediment=1100.0,
             gwstorage=100, bfcoeff=0.04, dscoeff=0.00, bfthreshold=1.001,
             mid_season_crop_coeff=0.95, p_coeff=0.8),
        dict(watershed='23_Intervening_Area_Sand_Harbor_2',  # 25 ha  Watershed_24
             extent=[-120.04760742187501, 39.16839998800286, -119.80728149414064, 39.35447606884594],
             map_center=[-119.92744445800783, 39.261499771230774],
             map_zoom=12,
             outlet=[-119.93014075643508, 39.19874614288978],
             landuse=None,
             cs=30, erod=0.000001,
             surf_runoff=0.003, lateral_flow=0.004, baseflow=0.005, sediment=1100.0,
             gwstorage=100, bfcoeff=0.04, dscoeff=0.00, bfthreshold=1.001,
             mid_season_crop_coeff=0.95, p_coeff=0.8),
        dict(watershed='23_Intervening_Area_Sand_Harbor_3',  # 33 ha  Watershed_25
             extent=[-120.04760742187501, 39.16839998800286, -119.80728149414064, 39.35447606884594],
             map_center=[-119.92744445800783, 39.261499771230774],
             map_zoom=12,
             outlet=[-119.92712434849918, 39.19623427594098],
             landuse=None,
             cs=30, erod=0.000001,
             surf_runoff=0.003, lateral_flow=0.004, baseflow=0.005, sediment=1100.0,
             gwstorage=100, bfcoeff=0.04, dscoeff=0.00, bfthreshold=1.001,
             mid_season_crop_coeff=0.95, p_coeff=0.8),
        dict(watershed='23_Intervening_Area_Sand_Harbor_4',  # 140 ha  Watershed_26
             extent=[-120.04760742187501, 39.16839998800286, -119.80728149414064, 39.35447606884594],
             map_center=[-119.92744445800783, 39.261499771230774],
             map_zoom=12,
             outlet=[-119.92704812670831, 39.190016450091775],
             landuse=None,
             cs=30, erod=0.000001,
             surf_runoff=0.003, lateral_flow=0.004, baseflow=0.005, sediment=1100.0,
             gwstorage=100, bfcoeff=0.04, dscoeff=0.00, bfthreshold=1.001,
             mid_season_crop_coeff=0.95, p_coeff=0.8),
        dict(watershed='24_Marlette_Creek',  # 1300 ha  Watershed_27
             extent=[-120.01396179199219, 39.019450429324046, -119.77363586425783, 39.20592074849823],
             map_center=[-119.89379882812501, 39.11274726579313],
             map_zoom=12,
             outlet=[-119.93270185597697, 39.16542835468725],
             landuse=None,
             cs=30, erod=0.000001,
             surf_runoff=0.003, lateral_flow=0.004, baseflow=0.005, sediment=1100.0,
             gwstorage=100, bfcoeff=0.04, dscoeff=0.00, bfthreshold=1.001,
             mid_season_crop_coeff=0.95, p_coeff=0.8),
        dict(watershed='25_Intervening_Area_Marlette_to_Secret_Harbor',  # 51 ha  Watershed_28
             extent=[-120.01396179199219, 39.019450429324046, -119.77363586425783, 39.20592074849823],
             map_center=[-119.89379882812501, 39.11274726579313],
             map_zoom=12,
             outlet=[-119.93090374225022, 39.150834255220026],
             landuse=None,
             cs=30, erod=0.000001,
             surf_runoff=0.003, lateral_flow=0.004, baseflow=0.005, sediment=1100.0,
             gwstorage=100, bfcoeff=0.04, dscoeff=0.00, bfthreshold=1.001,
             mid_season_crop_coeff=0.95, p_coeff=0.8),
        dict(watershed='25_Secret_Harbor_Creek',  # 510 ha  Watershed_29
             extent=[-120.01396179199219, 39.019450429324046, -119.77363586425783, 39.20592074849823],
             map_center=[-119.89379882812501, 39.11274726579313],
             map_zoom=12,
             outlet=[-119.93136079483678, 39.148367001968865],
             landuse=None,
             cs=30, erod=0.000001,
             surf_runoff=0.003, lateral_flow=0.004, baseflow=0.005, sediment=1100.0,
             gwstorage=100, bfcoeff=0.04, dscoeff=0.00, bfthreshold=1.001,
             mid_season_crop_coeff=0.95, p_coeff=0.8),
        dict(watershed='26_Bliss_Creek',  # 140 ha  Watershed_30
             extent=[-120.01396179199219, 39.019450429324046, -119.77363586425783, 39.20592074849823],
             map_center=[-119.89379882812501, 39.11274726579313],
             map_zoom=12,
             outlet=[-119.93642518249555, 39.143635771481485],
             landuse=None,
             cs=30, erod=0.000001,
             surf_runoff=0.003, lateral_flow=0.004, baseflow=0.005, sediment=1100.0,
             gwstorage=100, bfcoeff=0.04, dscoeff=0.00, bfthreshold=1.001,
             mid_season_crop_coeff=0.95, p_coeff=0.8),
        dict(watershed='27_Intervening_Area_Deadman_Point',  # 40 ha  Watershed_31
             extent=[-120.01396179199219, 39.019450429324046, -119.77363586425783, 39.20592074849823],
             map_center=[-119.89379882812501, 39.11274726579313],
             map_zoom=12,
             outlet=[-119.94066697186948, 39.14185550725643],
             landuse=None,
             cs=30, erod=0.000001,
             surf_runoff=0.003, lateral_flow=0.004, baseflow=0.005, sediment=1100.0,
             gwstorage=100, bfcoeff=0.04, dscoeff=0.00, bfthreshold=1.001,
             mid_season_crop_coeff=0.95, p_coeff=0.8),
        dict(watershed='28_Slaughterhouse_Creek',  # 1600 ha  Watershed_32
             extent=[-120.01396179199219, 39.019450429324046, -119.77363586425783, 39.20592074849823],
             map_center=[-119.89379882812501, 39.11274726579313],
             map_zoom=12,
             outlet=[-119.94656529513026, 39.1017421575381],
             landuse=None,
             cs=30, erod=0.000001,
             surf_runoff=0.003, lateral_flow=0.004, baseflow=0.005, sediment=1100.0,
             gwstorage=100, bfcoeff=0.04, dscoeff=0.00, bfthreshold=1.001,
             mid_season_crop_coeff=0.95, p_coeff=0.8),
        dict(watershed='29_Intervening_Area_Glenbrook_Bay_1',  # 88 ha  Watershed_33
             extent=[-120.01396179199219, 39.019450429324046, -119.77363586425783, 39.20592074849823],
             map_center=[-119.89379882812501, 39.11274726579313],
             map_zoom=12,
             outlet=[-119.9418433230724, 39.09864545553091],
             landuse=None,
             cs=30, erod=0.000001,
             surf_runoff=0.003, lateral_flow=0.004, baseflow=0.005, sediment=1100.0,
             gwstorage=100, bfcoeff=0.04, dscoeff=0.00, bfthreshold=1.001,
             mid_season_crop_coeff=0.95, p_coeff=0.8),
        dict(watershed='29_Intervening_Area_Glenbrook_Bay_2',  # 99 ha  Watershed_34
             extent=[-120.01396179199219, 39.019450429324046, -119.77363586425783, 39.20592074849823],
             map_center=[-119.89379882812501, 39.11274726579313],
             map_zoom=12,
             outlet=[-119.94062104067505, 39.09482976550799],
             landuse=None,
             cs=30, erod=0.000001,
             surf_runoff=0.003, lateral_flow=0.004, baseflow=0.005, sediment=1100.0,
             gwstorage=100, bfcoeff=0.04, dscoeff=0.00, bfthreshold=1.001,
             mid_season_crop_coeff=0.95, p_coeff=0.8),
        dict(watershed='29_Glenbrook_Creek',  # 1100 ha  Watershed_35
             extent=[-120.01396179199219, 39.019450429324046, -119.77363586425783, 39.20592074849823],
             map_center=[-119.89379882812501, 39.11274726579313],
             map_zoom=12,
             outlet=[-119.93952733643079, 39.08804461546371],
             landuse=None,
             cs=30, erod=0.000001,
             surf_runoff=0.003, lateral_flow=0.004, baseflow=0.005, sediment=1100.0,
             gwstorage=100, bfcoeff=0.04, dscoeff=0.00, bfthreshold=1.001,
             mid_season_crop_coeff=0.95, p_coeff=0.8),
        dict(watershed='30_North_Logan_House_Creek',  # 290 ha  Watershed_36
             extent=[-120.01396179199219, 39.019450429324046, -119.77363586425783, 39.20592074849823],
             map_center=[-119.89379882812501, 39.11274726579313],
             map_zoom=12,
             outlet=[-119.94139490719957, 39.068905396563665],
             landuse=None,
             cs=30, erod=0.000001,
             surf_runoff=0.003, lateral_flow=0.004, baseflow=0.005, sediment=1100.0,
             gwstorage=100, bfcoeff=0.04, dscoeff=0.00, bfthreshold=1.001,
             mid_season_crop_coeff=0.95, p_coeff=0.8),
        dict(watershed='31_Logan_House_Creek',  # 530 ha  Watershed_37
             extent=[-120.01396179199219, 39.019450429324046, -119.77363586425783, 39.20592074849823],
             map_center=[-119.89379882812501, 39.11274726579313],
             map_zoom=12,
             outlet=[-119.93525510941215, 39.066581990025206],
             landuse=None,
             cs=30, erod=0.000001,
             surf_runoff=0.003, lateral_flow=0.004, baseflow=0.005, sediment=1100.0,
             gwstorage=100, bfcoeff=0.04, dscoeff=0.00, bfthreshold=1.001,
             mid_season_crop_coeff=0.95, p_coeff=0.8),
        dict(watershed='32_Intervening_Area_Logan_Shoals_1',  # 31 ha  Watershed_38
             extent=[-120.01396179199219, 39.019450429324046, -119.77363586425783, 39.20592074849823],
             map_center=[-119.89379882812501, 39.11274726579313],
             map_zoom=12,
             outlet=[-119.94319963374946, 39.05922347741282],
             landuse=None,
             cs=30, erod=0.000001,
             surf_runoff=0.003, lateral_flow=0.004, baseflow=0.005, sediment=1100.0,
             gwstorage=100, bfcoeff=0.04, dscoeff=0.00, bfthreshold=1.001,
             mid_season_crop_coeff=0.95, p_coeff=0.8),
        dict(watershed='32_Intervening_Area_Logan_Shoals_2',  # 36 ha  Watershed_39
             extent=[-120.01396179199219, 39.019450429324046, -119.77363586425783, 39.20592074849823],
             map_center=[-119.89379882812501, 39.11274726579313],
             map_zoom=12,
             outlet=[-119.9445062251884, 39.05304180979089],
             landuse=None,
             cs=30, erod=0.000001,
             surf_runoff=0.003, lateral_flow=0.004, baseflow=0.005, sediment=1100.0,
             gwstorage=100, bfcoeff=0.04, dscoeff=0.00, bfthreshold=1.001,
             mid_season_crop_coeff=0.95, p_coeff=0.8),
        dict(watershed='32_Cave_Rock_Unnamed_Creek_at_Lincoln_Park',  # 150 ha  Watershed_40
             extent=[-120.01396179199219, 39.019450429324046, -119.77363586425783, 39.20592074849823],
             map_center=[-119.89379882812501, 39.11274726579313],
             map_zoom=12,
             outlet=[-119.94636531738409, 39.05011770248522],
             landuse=None,
             cs=30, erod=0.000001,
             surf_runoff=0.003, lateral_flow=0.004, baseflow=0.005, sediment=1100.0,
             gwstorage=100, bfcoeff=0.04, dscoeff=0.00, bfthreshold=1.001,
             mid_season_crop_coeff=0.95, p_coeff=0.8),
        dict(watershed='33_Lincoln_Creek',  # 700 ha  Watershed_41
             extent=[-120.01396179199219, 39.019450429324046, -119.77363586425783, 39.20592074849823],
             map_center=[-119.89379882812501, 39.11274726579313],
             map_zoom=12,
             outlet=[-119.94819197052668, 39.039895724271986],
             landuse=None,
             cs=30, erod=0.000001,
             surf_runoff=0.003, lateral_flow=0.004, baseflow=0.005, sediment=1100.0,
             gwstorage=100, bfcoeff=0.04, dscoeff=0.00, bfthreshold=1.001,
             mid_season_crop_coeff=0.95, p_coeff=0.8),
        dict(watershed='35_North_Zephyr_Creek',  # 680 ha  Watershed_42
             extent=[-120.06202697753908, 38.87045372777545, -119.8217010498047, 39.05731715424236],
             map_center=[-119.94186401367189, 38.963947050281696],
             map_zoom=12,
             outlet=[-119.94876901553465, 39.01494787512556],
             landuse=None,
             cs=30, erod=0.000001,
             surf_runoff=0.003, lateral_flow=0.004, baseflow=0.005, sediment=1100.0,
             gwstorage=100, bfcoeff=0.04, dscoeff=0.00, bfthreshold=1.001,
             mid_season_crop_coeff=0.95, p_coeff=0.8),
        dict(watershed='37_Zephyr_Creek',  # 430 ha  Watershed_43
             extent=[-120.06202697753908, 38.87045372777545, -119.8217010498047, 39.05731715424236],
             map_center=[-119.94186401367189, 38.963947050281696],
             map_zoom=12,
             outlet=[-119.94804448075419, 39.007631888060544],
             landuse=None,
             cs=30, erod=0.000001,
             surf_runoff=0.003, lateral_flow=0.004, baseflow=0.005, sediment=1100.0,
             gwstorage=100, bfcoeff=0.04, dscoeff=0.00, bfthreshold=1.001,
             mid_season_crop_coeff=0.95, p_coeff=0.8),
        dict(watershed='38_McFaul_Creek',  # 940 ha  Watershed_44
             extent=[-120.06202697753908, 38.87045372777545, -119.8217010498047, 39.05731715424236],
             map_center=[-119.94186401367189, 38.963947050281696],
             map_zoom=12,
             outlet=[-119.95345634105546, 38.99453069976447],
             landuse=None,
             cs=30, erod=0.000001,
             surf_runoff=0.003, lateral_flow=0.004, baseflow=0.005, sediment=1100.0,
             gwstorage=100, bfcoeff=0.04, dscoeff=0.00, bfthreshold=1.001,
             mid_season_crop_coeff=0.95, p_coeff=0.8),
        dict(watershed='39_Burke_Creek',  # 1200 ha  Watershed_45
             extent=[-120.06202697753908, 38.87045372777545, -119.8217010498047, 39.05731715424236],
             map_center=[-119.94186401367189, 38.963947050281696],
             map_zoom=12,
             outlet=[-119.94974779877337, 38.97605598069683],
             landuse=None,
             cs=30, erod=0.000001,
             surf_runoff=0.003, lateral_flow=0.004, baseflow=0.005, sediment=1100.0,
             gwstorage=100, bfcoeff=0.04, dscoeff=0.00, bfthreshold=1.001,
             mid_season_crop_coeff=0.95, p_coeff=0.8)
    ]

    scenarios = [
        dict(scenario='SimFire.fccsFuels_obs_cli',
             landuse=None,
             lc_lookup_fn='ki5krcs.csv',
             cfg='lt-fire-snow',
             climate='copyCurCond'),
        dict(scenario='SimFire.landisFuels_obs_cli',
             landuse=None,
             lc_lookup_fn='ki5krcs.csv',
             cfg='lt-fire-future-snow',
             climate='copyCurCond'),
        dict(scenario='SimFire.landisFuels_fut_cli_A2',
             landuse=None,
             lc_lookup_fn='ki5krcs.csv',
             cfg='lt-fire-future-snow',
             climate='future'),
        dict(scenario='CurCond',
             landuse=None,
             lc_lookup_fn='ki5krcs.csv'),
        dict(scenario='PrescFire',
             landuse=[(not_shrub_selector, 110), (shrub_selector, 122)],
             lc_lookup_fn='ki5krcs.csv',
             climate='copyCurCond'),
        dict(scenario='LowSev',
             landuse=[(not_shrub_selector, 106), (shrub_selector, 121)],
             lc_lookup_fn='ki5krcs.csv',
             climate='copyCurCond'),
        dict(scenario='ModSev',
             landuse=[(not_shrub_selector, 118), (shrub_selector, 120)],
             lc_lookup_fn='ki5krcs.csv',
             climate='copyCurCond'),
        dict(scenario='HighSev',
             landuse=[(not_shrub_selector, 105), (shrub_selector, 119)],
             lc_lookup_fn='ki5krcs.csv',
             climate='copyCurCond'),
        dict(scenario='Thinn96',
             landuse=[(not_shrub_selector, 123)],
             lc_lookup_fn='ki5krcs.csv',
             climate='copyCurCond'),
        dict(scenario='Thinn93',
             landuse=[(not_shrub_selector, 115)],
             lc_lookup_fn='ki5krcs.csv',
             climate='copyCurCond'),
        dict(scenario='Thinn85',
             landuse=[(not_shrub_selector, 117)],
             lc_lookup_fn='ki5krcs.csv',
             climate='copyCurCond'),  # <- EXAMPLE FOR COPYING CLIMATE
    ]

    skip_completed = True

    projects = []

    wc = sys.argv[-1]
    if '.py' in wc:
        wc = None

    for scenario in scenarios:
        for watershed in watersheds:
            projects.append(deepcopy(watershed))
            projects[-1]['cfg'] = scenario.get('cfg', 'lt-wepp_bd16b69-snow')
            projects[-1]['landuse'] = scenario['landuse']
            projects[-1]['lc_lookup_fn'] = scenario.get('lc_lookup_fn', 'landSoilLookup.csv')
            projects[-1]['climate'] = scenario.get('climate', 'observed')
            projects[-1]['scenario'] = scenario['scenario']
            projects[-1]['wd'] = 'lt_202010_%s_%s' % (watershed['watershed'], scenario['scenario'])

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
            lc_lookup_fn = proj['lc_lookup_fn']

            watershed = proj['watershed']
            scenario = proj['scenario']

            if wc is not None:
                if not wc in wd:
                    continue

            if skip_completed:
                if _exists(_join(wd, 'wepp', 'output', 'loss_pw0.txt')):
                    log_print('has loss_pw0.txt... skipping.')
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
            topaz.build_channels(csa=5, mcl=60)
            topaz.set_outlet(*outlet)
            sleep(0.5)

            log_print('building subcatchments')
            topaz.build_subcatchments()

            log_print('abstracting watershed')
            wat = Watershed.getInstance(wd)
            wat.abstract_watershed()
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
                    _topaz_ids = selector(landuse, None)
                    bare_tops = bare_or_sodgrass_or_bunchgrass_selector(landuse, None)
                    _topaz_ids = [top for top in _topaz_ids if top not in bare_tops]

                    landuse.modify(_topaz_ids, dom)
                    tops.extend(_topaz_ids)

            log_print('building soils')
            if _exists(_join(wd, 'lt.nodb')):
                lt = LakeTahoe.getInstance(wd)
                lt.lc_lookup_fn = lc_lookup_fn

            soils = Soils.getInstance(wd)
            soils.mode = SoilsMode.Gridded
            soils.build()

            log_print('building climate')

            if climate_mode == 'observed':
                climate = Climate.getInstance(wd)
                stations = climate.find_closest_stations()
                climate.input_years = 30
                climate.climatestation = stations[0]['id']

                climate.climate_mode = ClimateMode.Observed
                climate.climate_spatialmode = ClimateSpatialMode.Multiple
                climate.set_observed_pars(start_year=1990, end_year=2019)
            elif climate_mode == 'future':
                climate = Climate.getInstance(wd)
                stations = climate.find_closest_stations()
                climate.input_years = 30
                climate.climatestation = stations[0]['id']

                climate.climate_mode = ClimateMode.Future
                climate.climate_spatialmode = ClimateSpatialMode.Single
                climate.set_future_pars(start_year=2018, end_year=2018 + 30)
                # climate.set_orig_cli_fn(_join(climate._future_clis_wc, 'Ward_Creek_A2.cli'))
            elif climate_mode == 'vanilla':
                climate = Climate.getInstance(wd)
                stations = climate.find_closest_stations()
                climate.input_years = 30
                climate.climatestation = stations[0]['id']

                climate.climate_mode = ClimateMode.Vanilla
                climate.climate_spatialmode = ClimateSpatialMode.Single
                # climate.set_orig_cli_fn(_join(climate._future_clis_wc, 'Ward_Creek_A2.cli'))
            elif 'copy' in climate_mode:
                src_wd = 'lt_202010_%s_%s' % (watershed, climate_mode[4:])
                shutil.rmtree(_join(wd, 'climate'))
                shutil.copytree(_join(src_wd, 'climate'), _join(wd, 'climate'))
                with open(_join(src_wd, 'climate.nodb')) as fp:
                    contents = fp.read()

                with open(_join(wd, 'climate.nodb'), 'w') as fp:
                    fp.write(contents.replace(src_wd, wd))

            else:
                raise Exception("Unknown climate_mode")

            if 'copy' not in climate_mode:
                climate.build(verbose=1)

            log_print('prepping wepp')
            wepp = Wepp.getInstance(wd)
            wepp.parse_inputs(proj)

            wepp.prep_hillslopes()

            log_print('running hillslopes')
            wepp.run_hillslopes()

            log_print('prepping watershed')
            wepp = Wepp.getInstance(wd)
            wepp.prep_watershed(erodibility=proj['erod'], critical_shear=proj['cs'])
            wepp._prep_pmet(mid_season_crop_coeff=proj['mid_season_crop_coeff'], p_coeff=proj['p_coeff'])

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
