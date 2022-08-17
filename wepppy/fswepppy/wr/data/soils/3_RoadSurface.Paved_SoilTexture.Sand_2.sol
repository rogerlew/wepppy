7778
# 
# File:    3psand2.sol
# Created: 05 July 2000; 08 Oct 2003
# Author:  H. Rhee; Darrell Anderson
# Contact: Bill Elliot, Soil and Water Engineering
# U.S. Forest Service Rocky Mountain Research Station
# http://forest.moscowfsl.wsu.edu/fswepp
# 
# Paved surface outsloped
# 
# wepppy.wepp.soils.utils.WeppSoilUtil 7778 migration
#   Build Date: 2022-08-16 15:09:06.951707
#   Source File: :og/3psand2.sol
# 
# ofe=0,horizon0 bd default value of 1.4
# ofe=0,horizon0 fc estimated using Rosetta(clay=5, sand=70, bd=None, silt=25)
# ofe=0,horizon0 wp estimated using Rosetta(clay=5, sand=70, bd=None, silt=25)
# ofe=0,horizon0 ksat estimated using Rosetta(clay=5, sand=70, bd=None, silt=25)
# ofe=0,horizon0 anisotropy estimated using Rosetta(clay=5, sand=70, bd=None, silt=25)
# ofe=1,horizon0 bd default value of 1.4
# ofe=1,horizon0 fc estimated using Rosetta(clay=5, sand=60, bd=None, silt=35)
# ofe=1,horizon0 wp estimated using Rosetta(clay=5, sand=60, bd=None, silt=35)
# ofe=1,horizon0 ksat estimated using Rosetta(clay=5, sand=60, bd=None, silt=35)
# ofe=1,horizon0 anisotropy estimated using Rosetta(clay=5, sand=60, bd=None, silt=35)
# ofe=2,horizon0 bd default value of 1.4
# ofe=2,horizon0 fc estimated using Rosetta(clay=5, sand=60, bd=None, silt=35)
# ofe=2,horizon0 wp estimated using Rosetta(clay=5, sand=60, bd=None, silt=35)
# ofe=2,horizon0 ksat estimated using Rosetta(clay=5, sand=60, bd=None, silt=35)
# ofe=2,horizon0 anisotropy estimated using Rosetta(clay=5, sand=60, bd=None, silt=35)
Plume for road (07/05/00)
3 0
'Road'	 'sandy loam'	 1	 0.6	 0.5	 5	 1e-06	 10.0
	200	 1.4	 64.3506	 1.0	 0.1829	 0.0729	 70	 5	 0.01	 4	 urr
1 10000.0 64.3506
'Fill'	 'sandy loam'	 1	 0.18	 0.45	 1600000.0	 0.0004	 2.0
	400	 1.4	 54.463	 1.0	 0.1938	 0.0809	 60	 5	 3	 4	 ufr
1 10000.0 54.463
'Forest'	 'sandy loam'	 1	 0.05	 0.4	 130000.0	 0.0004	 2.0
	400	 1.4	 54.463	 1.0	 0.1938	 0.0809	 60	 5	 6	 5	 ubr
1 10000.0 54.463