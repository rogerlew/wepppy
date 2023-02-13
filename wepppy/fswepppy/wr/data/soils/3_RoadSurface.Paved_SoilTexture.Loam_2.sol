7778
# 
# File:    3ploam2.sol
# Created: 28 July 2000; 08 Oct 2003
# Author:  H. Rhee; Darrell Anderson
# Contact: Bill Elliot, Soil and Water Engineering
# U.S. Forest Service Rocky Mountain Research Station
# http://forest.moscowfsl.wsu.edu/fswepp
# 
# Paved surface outsloped
# 
# wepppy.wepp.soils.utils.WeppSoilUtil 7778 migration
#   Build Date: 2022-08-16 15:09:09.109326
#   Source File: :og/3ploam2.sol
# 
# ofe=0,horizon0 bd default value of 1.4
# ofe=0,horizon0 fc estimated using Rosetta(clay=20, sand=45, bd=None, silt=35)
# ofe=0,horizon0 wp estimated using Rosetta(clay=20, sand=45, bd=None, silt=35)
# ofe=0,horizon0 ksat estimated using Rosetta(clay=20, sand=45, bd=None, silt=35)
# ofe=0,horizon0 anisotropy estimated using Rosetta(clay=20, sand=45, bd=None, silt=35)
# ofe=1,horizon0 bd default value of 1.4
# ofe=1,horizon0 fc estimated using Rosetta(clay=20, sand=40, bd=None, silt=40)
# ofe=1,horizon0 wp estimated using Rosetta(clay=20, sand=40, bd=None, silt=40)
# ofe=1,horizon0 ksat estimated using Rosetta(clay=20, sand=40, bd=None, silt=40)
# ofe=1,horizon0 anisotropy estimated using Rosetta(clay=20, sand=40, bd=None, silt=40)
# ofe=2,horizon0 bd default value of 1.4
# ofe=2,horizon0 fc estimated using Rosetta(clay=20, sand=40, bd=None, silt=40)
# ofe=2,horizon0 wp estimated using Rosetta(clay=20, sand=40, bd=None, silt=40)
# ofe=2,horizon0 ksat estimated using Rosetta(clay=20, sand=40, bd=None, silt=40)
# ofe=2,horizon0 anisotropy estimated using Rosetta(clay=20, sand=40, bd=None, silt=40)
Plume for road (07/28/00)
3 0
'Road'	 'loam'	 1	 0.6	 0.5	 5	 1e-06	 10.0
	200	 1.4	 12.2444	 1.0	 0.2558	 0.1341	 45	 20	 0.01	 16	 urr
1 10000.0 12.2444
'Fill'	 'loam'	 1	 0.18	 0.45	 2300000.0	 0.0003	 2.0
	400	 1.4	 12.3071	 1.0	 0.2535	 0.1345	 40	 20	 3	 17	 ufr
1 10000.0 12.3071
'Forest'	 'loam'	 1	 0.05	 0.4	 120000.0	 0.0002	 2.0
	400	 1.4	 12.3071	 1.0	 0.2535	 0.1345	 40	 20	 6	 18	 ubr
1 10000.0 12.3071