7778
# 
# File:    3psilt1.sol
# Created: 02 August 2000; 08 Oct 2003
# Author:  H. Rhee; Darrell Anderson
# Contact: Bill Elliot, Soil and Water Engineering
# U.S. Forest Service Rocky Mountain Research Station
# http://forest.moscowfsl.wsu.edu/fswepp
# 
# Paved surface for insloped, bare ditch
# (paved surface Ki & Ks and native surface Kr & tau_c)
# 
# wepppy.wepp.soils.utils.WeppSoilUtil 7778 migration
#   Build Date: 2022-08-16 15:09:06.678235
#   Source File: :og/3psilt1.sol
# 
# ofe=0,horizon0 bd default value of 1.4
# ofe=0,horizon0 fc estimated using Rosetta(clay=15, sand=35, bd=None, silt=50)
# ofe=0,horizon0 wp estimated using Rosetta(clay=15, sand=35, bd=None, silt=50)
# ofe=0,horizon0 ksat estimated using Rosetta(clay=15, sand=35, bd=None, silt=50)
# ofe=0,horizon0 anisotropy estimated using Rosetta(clay=15, sand=35, bd=None, silt=50)
# ofe=1,horizon0 bd default value of 1.4
# ofe=1,horizon0 fc estimated using Rosetta(clay=15, sand=30, bd=None, silt=55)
# ofe=1,horizon0 wp estimated using Rosetta(clay=15, sand=30, bd=None, silt=55)
# ofe=1,horizon0 ksat estimated using Rosetta(clay=15, sand=30, bd=None, silt=55)
# ofe=1,horizon0 anisotropy estimated using Rosetta(clay=15, sand=30, bd=None, silt=55)
# ofe=2,horizon0 bd default value of 1.4
# ofe=2,horizon0 fc estimated using Rosetta(clay=15, sand=30, bd=None, silt=55)
# ofe=2,horizon0 wp estimated using Rosetta(clay=15, sand=30, bd=None, silt=55)
# ofe=2,horizon0 ksat estimated using Rosetta(clay=15, sand=30, bd=None, silt=55)
# ofe=2,horizon0 anisotropy estimated using Rosetta(clay=15, sand=30, bd=None, silt=55)
Plume for road (08/02/00)
3 0
'Road'	 'silt loam'	 1	 0.6	 0.5	 5	 0.0003	 2.0
	200	 1.4	 21.3439	 1.0	 0.2257	 0.1171	 35	 15	 0.01	 12	 urr
1 10000.0 21.3439
'Fill'	 'silt loam'	 1	 0.18	 0.45	 2300000.0	 0.0003	 2.0
	400	 1.4	 21.8754	 1.0	 0.2241	 0.1177	 30	 15	 3	 13	 ufr
1 10000.0 21.8754
'Forest'	 'silt loam'	 1	 0.05	 0.4	 120000.0	 0.0002	 2.0
	400	 1.4	 21.8754	 1.0	 0.2241	 0.1177	 30	 15	 6	 14	 ubr
1 10000.0 21.8754