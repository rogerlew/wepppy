# -*- coding: utf-8 -*-
"""
Created on Mon Dec 27 15:14:57 2021

@author: Anurag

Ash Model:
1) This model works on single OFE.
2) Uses WEPP's daily water file.
3) Model operates on runoff and infiltration amount from WEPP.
4)


Assumptions:
1)
2)
3)

"""
import math
import os
import sys
import glob
from time import time
import pandas as pd
import multiprocessing as mp
import matplotlib.pyplot as plt
pd.options.mode.chained_assignment = None  # default='warn'


def ash_model(df, fname):

    print('running ash model on wat file: ', os.path.basename(wat).split('.')[0])

    # define fire day in julian
    fireDay = 217

    # define parameters
    iniBulkDen = 0.31  # Initial bulk density, gm/cm3
    finBulkDen = 0.62  # Final bulk density, gm/cm3
    bulkDenFac = 0.005  # Bulk density factor
    parDen = 1.2  # Ash particle density, gm/cm3
    decompFac = 0.00018  # Ash decomposition factor, per day
    iniErod = 1  # Initial erodibility, t/ha
    finErod = 0.01  # Final erodibility, t/ha
    roughnessLimit = 1  # Roughness limit, mm
    iniAshDepth = 14  # Initial ash depth, mm
    iniAshLoad = 10 * iniAshDepth * iniBulkDen   # Initial ash load, t/ha

    # update year
    df.insert(1, 'Year', df.apply(lambda x: x['Y_#'] if x['J_#'] >= fireDay else x['Y_#'] - 1, axis=1))

    # update julian
    df.insert(2, 'Julian', df.groupby(['Year']).cumcount() + 1)

    # calulate infiltration
    df['Infil_mm'] = df.apply(lambda x: x['RM_mm'] - x['Q_mm'], axis=1)

    # cumulative infiltration
    df['Cum_Infil_mm'] = df.groupby(['Year'])['Infil_mm'].cumsum(axis=0)

    # cumulative surface runoff
    df['Cum_Q_mm'] = df.groupby(['Year'])['Q_mm'].cumsum(axis=0)

    # calculate bulk density as a function of cumulative infiltration
    df['Bulk_density_gmpcm3'] = df.apply(lambda x: finBulkDen + (iniBulkDen - finBulkDen) * math.exp(-bulkDenFac * x['Cum_Infil_mm']), axis=1)

    # calculate porosity for water holding capacity of ash layer
    df['Porosity'] = df.apply(lambda x: 1 - (x['Bulk_density_gmpcm3']/parDen), axis=1)

    # compute daily values
    df.loc[0, 'Available_ash_tonspha'] = iniAshLoad
    df.loc[0, 'Ash_depth_mm'] = df.loc[0, 'Available_ash_tonspha'] * df.loc[0, 'Bulk_density_gmpcm3']

    for t in range(1, len(df)):

        # runoff from ash layer
        if df.loc[t-1, 'Q_mm'] > ((df.loc[t-1, 'Available_ash_tonspha']/(10 * df.loc[t-1, 'Bulk_density_gmpcm3'])) * df.loc[t-1, 'Porosity']):
            df.loc[t-1, 'Ash_runoff_mm'] = max(0, df.loc[t-1, 'Q_mm'] - ((df.loc[t-1, 'Available_ash_tonspha']/(10 * df.loc[t-1, 'Bulk_density_gmpcm3'])) * df.loc[t-1, 'Porosity']))
        else:
            df.loc[t-1, 'Ash_runoff_mm'] = 0

        # ash transport and ash delivery from hillslope
        if df.loc[t-1, 'Ash_runoff_mm'] > 0:
            df.loc[t-1, 'Ash_transport_tonspha'] = (iniErod - finErod) * ((df.loc[t-1, 'Bulk_density_gmpcm3'] - finBulkDen)/(iniBulkDen - finBulkDen)) + finErod
            df.loc[t-1, 'Ash_out_tonspha'] = max(0, min(df.loc[t-1, 'Available_ash_tonspha'], df.loc[t-1, 'Ash_runoff_mm'] * df.loc[t-1, 'Ash_transport_tonspha']))
        else:
            df.loc[t-1, 'Ash_transport_tonspha'] = 0
            df.loc[t-1, 'Ash_out_tonspha'] = 0

        # available ash
        if df.loc[t, 'Julian'] > 1:
            if df.loc[t-1, 'Ash_depth_mm'] < roughnessLimit:
                df.loc[t, 'Available_ash_tonspha'] = 0
            else:
                df.loc[t, 'Available_ash_tonspha'] = df.loc[t-1, 'Available_ash_tonspha'] * math.exp(-decompFac * df.loc[t, 'Infil_mm']) - df.loc[t-1, 'Ash_out_tonspha']
        else:
            df.loc[t, 'Available_ash_tonspha'] = iniAshLoad

        # ash depth
        df.loc[t, 'Ash_depth_mm'] = df.loc[t, 'Available_ash_tonspha']/(10 * df.loc[t, 'Bulk_density_gmpcm3'])

    # cumulative runoff from ash layer
    df['Cum_ash_runoff_mm'] = df.groupby(['Year'])['Ash_runoff_mm'].cumsum(axis=0)

    # cumulative ash delive from hillslope
    df['Cum_ash_out_tonspha'] = df.groupby(['Year'])['Ash_out_tonspha'].cumsum(axis=0)

    # remove the first and the last year
    df = df[(df['Year'] > df['Year'].iloc[0]) & (df['Year'] < df['Year'].iloc[-1])]

    # reset and rename index
    df.reset_index(drop=True, inplace=True)
    df.index.rename("SNo.", inplace=True)

    # drop columns
    df = df.drop(['Y_#', 'J_#', 'Date'], axis=1)

    # Update date
    df.insert(0, 'Date', pd.date_range("01-01-" + str(df['Year'].iloc[0]), periods=len(df), freq='D'))

    # write ash output file
    df.to_csv(fname + '_ash.csv')

    # graphing

    # line plot
    fig = plt.figure()
    ax = plt.gca()
    df.plot(kind='line', x='Date', y='Cum_ash_runoff_mm', color='blue', ax=ax)
    df.plot(secondary_y=True, kind='line', x='Date', y='Cum_ash_out_tonspha', color='red', ax=ax)
    fig.savefig(fname + '_ash.png')

    # scatter plot
    fig2 = plt.figure()
    ax = plt.gca()
    df.plot(kind='scatter', x='Cum_ash_runoff_mm', y='Cum_ash_out_tonspha', color='blue', ax=ax)
    fig2.savefig(fname + '_ash_scatter.png')


def get_wat_input(wat):
    t0 = time()
    print(' ')
    print('read wepp water file: ', os.path.basename(wat).split('.')[0])
    watr = pd.read_table(wat, skiprows=skipped_rows, sep='\s+', header=None, names=col_names)

    # make starting/ending date for stochastic climate
    if watr['Y_#'].iloc[0] == 1:
        starting = '1/1/' + str(watr['Y_#'].iloc[0] + 1900)
        ending = '12/31/' + str(watr['Y_#'].iloc[-1] + 1900)
    # make starting/ending date for observed climate
    else:
        starting = '1/1/' + str(watr['Y_#'].iloc[0])
        ending = '12/31/' + str(watr['Y_#'].iloc[-1])

    # create ash df
    ash_df = pd.DataFrame()

    # get selected variables from watr df to ash df
    ash_df = watr[['J_#', 'Y_#', 'P_mm', 'RM_mm', 'Q_mm']]

    # insert date column to ash df
    ash_df.insert(0, 'Date', pd.date_range(start=starting, end=ending))

    ash_model(ash_df, os.path.basename(wat).split('.')[0][:-4])


if __name__ == '__main__':

    ######## Change working dir ##########################
    wdir = os.path.dirname(os.path.realpath(sys.argv[0]))
    os.chdir(wdir)
    ######################################################

    out_path = os.path.join(wdir, 'out')

    # process watr.txt file to get SWE and compare it with observed SWE
    print()
    # Header row
    col_names = "OFE J Y P RM Q Ep Es Er Dp UpStrmQ SubRIn latqcc Total-Soil-Water frozwt Snow-Water QOFE Tile Irr Area"
    col_names = col_names.split()

    # Units row
    units = "# # # mm mm mm mm mm mm mm mm mm mm mm mm mm mm mm mm m^2"
    units = units.split()

    # Concatenating header and units
    # def concat_func(x, y):
    #     return x + " (" + y + ")"
    concat_func = lambda x, y: x + "_" + y
    col_names = list(map(concat_func, col_names, units))

    # Skip all rows before actual data
    skipped_rows = range(0, 23)

    # get WEPP water file from ./out directory
    for wat in glob.glob(wdir + '\\out\\*_wat.txt'):
        get_wat_input(wat)


