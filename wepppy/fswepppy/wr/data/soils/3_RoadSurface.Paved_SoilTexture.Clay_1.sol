7778
# 
# File:    3pclay1.sol
# Created: 28 July 2000; 08 Oct 2003
# Author:  H. Rhee; Darrell Anderson
# Contact: Bill Elliot, Soil and Water Engineering
# U.S. Forest Service Rocky Mountain Research Station
# http://forest.moscowfsl.wsu.edu/fswepp
# 
# Paved surface for insloped, bare ditch condition (w/ paved surface Ki & Ks and native surface Kr & tau_c)
# 
# wepppy.wepp.soils.utils.WeppSoilUtil 7778 migration
#   Build Date: 2022-08-16 15:09:05.975289
#   Source File: :og/3pclay1.sol
# 
# ofe=0,horizon0 bd default value of 1.4
# ofe=0,horizon0 fc estimated using Rosetta(clay=30, sand=35, bd=None, silt=35)
# ofe=0,horizon0 wp estimated using Rosetta(clay=30, sand=35, bd=None, silt=35)
# ofe=0,horizon0 ksat estimated using Rosetta(clay=30, sand=35, bd=None, silt=35)
# ofe=0,horizon0 anisotropy estimated using Rosetta(clay=30, sand=35, bd=None, silt=35)
# ofe=1,horizon0 bd default value of 1.4
# ofe=1,horizon0 fc estimated using Rosetta(clay=30, sand=30, bd=None, silt=40)
# ofe=1,horizon0 wp estimated using Rosetta(clay=30, sand=30, bd=None, silt=40)
# ofe=1,horizon0 ksat estimated using Rosetta(clay=30, sand=30, bd=None, silt=40)
# ofe=1,horizon0 anisotropy estimated using Rosetta(clay=30, sand=30, bd=None, silt=40)
# ofe=2,horizon0 bd default value of 1.4
# ofe=2,horizon0 fc estimated using Rosetta(clay=30, sand=30, bd=None, silt=40)
# ofe=2,horizon0 wp estimated using Rosetta(clay=30, sand=30, bd=None, silt=40)
# ofe=2,horizon0 ksat estimated using Rosetta(clay=30, sand=30, bd=None, silt=40)
# ofe=2,horizon0 anisotropy estimated using Rosetta(clay=30, sand=30, bd=None, silt=40)
Plume for road (08/02/00)
3 0
'Road'	 'clay loam'	 1	 0.6	 0.5	 5	 0.0002	 2.0
	200	 1.4	 7.9542	 1.0	 0.2885	 0.1645	 35	 30	 0.01	 24	 urr
1 10000.0 7.9542
'Fill'	 'clay loam'	 1	 0.18	 0.45	 1000000.0	 0.0002	 1.4
	400	 1.4	 9.5377	 1.0	 0.2849	 0.1635	 30	 30	 3	 26	 ufr
1 10000.0 9.5377
'Forest'	 'clay loam'	 1	 0.05	 0.4	 10000.0	 0.0002	 1.4
	400	 1.4	 9.5377	 1.0	 0.2849	 0.1635	 30	 30	 6	 27	 ubr
1 10000.0 9.5377