from __future__ import annotations

from pathlib import Path

import pytest

from wepppy.wepp.management import read_management
from wepppy.wepp.management.utils import ManagementMultipleOfeSynth


HIGH_SEVERITY_FIRE_MAN = """98.4
#
#
#
#

1 # number of OFE's
1 # (total) years in simulation

#######################
# Plant Section       #
#######################

1  # Number of plant scenarios


Tah_6892
With no Senescence or decomposition
(null)
W. Elliot 05/10
1  #landuse
WeppWillSet
14.00000 3.00000 0.00000 2.00000 5.00000 5.00000 0.00000 0.30000 1.00000 0.00500
0.50000 1.00000 0.45000 0.99000 17.00000 0.00000 0.42000 0.20000
2  # mfo - <non fragile>
0.00000 0.00000 20.00000 0.10000 0.50000 0.30000 0.33000 0.20000 90 40.00000
-40.00000 2.00000 0.00000

#######################
# Operation Section   #
#######################

0  # Number of operation scenarios

###############################
# Initial Conditions Section  #
###############################

1  # Number of initial scenarios


Tah_4436
For no growth, no decomp, no senescence

W. Elliot  05/10
1  #landuse
1.10000 0.40000 330 1000 0.00000 0.30000
1 # iresd  <Tah_6892>
2 # mang perennial
400.00000 0.06000 0.30000 0.06000 0.00000
1  # rtyp - temporary
0.00000 0.00000 0.00000 0.00000 0.00000
0.20000 0.20000




############################
# Surface Effects Section  #
############################

0  # Number of Surface Effects Scenarios

#######################
# Contouring Section  #
#######################

0  # Number of contour scenarios

#######################
# Drainage Section    #
#######################

0  # Number of drainage scenarios

#######################
# Yearly Section      #
#######################

1  # looper; number of Yearly Scenarios
#
# Yearly scenario 1 of 1
#
Year 1 
(null)
(null)
(null)
1  # landuse <cropland>
1  # plant growth scenario
0  # surface effect scenario
0  # contour scenario
0  # drainage scenario
2 # management <perennial>
   0 # senescence date 
   0 # perennial plant date --- 0 /0
   0 # perennial stop growth date --- 0/0
   0.0000  # row width
   3  # neither cut or grazed

#######################
# Management Section  #
#######################

Manage
description 1
description 2
description 3
1   # number of OFE's
    1   # initial condition index
1  # rotation repeats
1  # years in rotation

#
# Rotation 1: year 1 to 1
#

   1	#  <plants/yr 1> - OFE: 1>
      1	# year index

"""

LOW_SEVERITY_FIRE_MAN = """98.4
#
#
#
#

1 # number of OFE's
1 # (total) years in simulation

#######################
# Plant Section       #
#######################

1  # Number of plant scenarios


Tah_2823
With no Senescence or decomposition
(null)
W. Elliot 05/10
1  #landuse
WeppWillSet
14.00000 3.00000 0.00000 2.00000 5.00000 5.00000 0.00000 0.30000 1.00000 0.00500
0.50000 1.00000 0.55000 0.99000 17.00000 0.00000 0.42000 0.30000
2  # mfo - <non fragile>
0.00000 0.00000 20.00000 0.10000 0.50000 0.30000 0.33000 0.20000 90 40.00000
-40.00000 4.00000 0.00000

#######################
# Operation Section   #
#######################

0  # Number of operation scenarios

###############################
# Initial Conditions Section  #
###############################

1  # Number of initial scenarios

Tah_2307
For no growth, no decomp, no senescence

W. Elliot  05/10
1  #landuse
1.10000 0.75000 330 1000 0.00000 0.85000
1 # iresd  <Tah_2823>
2 # mang perennial
400.00000 0.04000 0.85000 0.04000 0.00000
1  # rtyp - temporary
0.00000 0.00000 0.00000 0.00000 0.00000
0.10000 0.10000

############################
# Surface Effects Section  #
############################

0  # Number of Surface Effects Scenarios

#######################
# Contouring Section  #
#######################

0  # Number of contour scenarios

#######################
# Drainage Section    #
#######################

0  # Number of drainage scenarios

#######################
# Yearly Section      #
#######################

1  # looper; number of Yearly Scenarios
#
# Yearly scenario 1 of 1
#
Year 1 
(null)
(null)
(null)
1  # landuse <cropland>
1  # plant growth scenario
0  # surface effect scenario
0  # contour scenario
0  # drainage scenario
2 # management <perennial>
   0 # senescence date 
   0 # perennial plant date --- 0 /0
   0 # perennial stop growth date --- 0/0
   0.0000  # row width
   3  # neither cut or grazed

#######################
# Management Section  #
#######################

Manage
description 1
description 2
description 3
1   # number of OFE's
    1   # initial condition index
1  # rotation repeats
1  # years in rotation

#
# Rotation 1: year 1 to 1
#

   1	#  <plants/yr 1> - OFE: 1>
      1	# year index

"""

SHRUB_MAN = """98.4
#
#
#
#

1 # number of OFE's
1 # (total) years in simulation

#######################
# Plant Section       #
#######################

1  # Number of plant scenarios


Shr_6877
Shrub prairie including sage and Pinyon-Juniper
for disturbed WEPP with WSU Senescence Modifications
W. Elliot  01/07
1  #landuse
WeppWillSet
1.00000 3.00000 0.00000 2.00000 5.00000 5.00000 0.00000 1.20000 0.40000 0.10000
0.50000 0.40000 0.90000 0.99000 13.00000 0.00000 0.42000 1.00000
2  # mfo - <non fragile>
0.00000 0.00000 20.00000 0.10000 0.50000 0.40000 0.33000 0.20000 45 40.00000
-40.00000 2.00000 0.00000

#######################
# Operation Section   #
#######################

0  # Number of operation scenarios




###############################
# Initial Conditions Section  #
###############################

1  # Number of initial scenarios


Shr_7020
Shrub Rangeland including sage and Pinyon Juniper
for WEPP with WSU senescence modification
W. Elliot 01/07
1  #landuse
1.10000 0.40000 1000 1000 0.00000 0.85000
1 # iresd  <Shr_6877>
2 # mang perennial
1000.00000 0.10000 0.85000 0.10000 0.00000
1  # rtyp - temporary
0.00000 0.00000 0.10000 0.20000 0.00000
0.20000 0.20000




############################
# Surface Effects Section  #
############################

0  # Number of Surface Effects Scenarios



#######################
# Contouring Section  #
#######################

0  # Number of contour scenarios


#######################
# Drainage Section    #
#######################

0  # Number of drainage scenarios


#######################
# Yearly Section      #
#######################

1  # looper; number of Yearly Scenarios
#
# Yearly scenario 1 of 1
#
Year 1



1  # landuse <cropland>
1  # plant growth scenario
0  # surface effect scenario
0  # contour scenario
0  # drainage scenario
2 # management <perennial>
   0 # senescence date
   0 # perennial plant date --- 0 /0
   0 # perennial stop growth date --- 0/0
   0.0000  # row width
   3  # neither cut or grazed


#######################
# Management Section  #
#######################

Manage
description 1
description 2
description 3
1   # number of OFE's
    1   # initial condition index
1  # rotation repeats
1  # years in rotation

#
# Rotation 1: year 1 to 1
#

   1	#  <plants/yr 1> - OFE: 1>
      1	# year index

"""


def _write_management(tmp_path: Path, name: str, contents: str) -> Path:
    path = tmp_path / name
    path.write_text(contents)
    return path


@pytest.mark.unit
def test_management_multiple_ofe_synth(tmp_path: Path) -> None:
    man_paths = [
        _write_management(tmp_path, "high.man", HIGH_SEVERITY_FIRE_MAN),
        _write_management(tmp_path, "low.man", LOW_SEVERITY_FIRE_MAN),
        _write_management(tmp_path, "shrub.man", SHRUB_MAN),
    ]

    stack = [read_management(str(path)) for path in man_paths]
    synth = ManagementMultipleOfeSynth(stack=stack)

    output_path = tmp_path / "synthesized.man"
    synth.write(str(output_path))
    assert output_path.exists()

    result = read_management(str(output_path))

    assert result.nofe == result.man.nofes == 3
    assert len(result.plants) == 3
    assert len(result.ops) == 0
    assert len(result.inis) == 3
    assert len(result.years) == 3

    assert result.plants[0].name == "Tah_6892"
    assert result.plants[1].name == "OFE2_Tah_2823"
    assert result.plants[2].name == "OFE3_Shr_6877"

    assert result.inis[0].name == "Tah_4436"
    assert result.inis[1].name == "OFE2_Tah_2307"
    assert result.inis[2].name == "OFE3_Shr_7020"

    assert result.years[0].name == "Year 1"
    assert result.years[1].name == "OFE2_Year 1"
    assert result.years[2].name == "OFE3_Year 1"

    ofe1_ini_ref = result.man.ofeindx[0]
    assert ofe1_ini_ref.loop_name == "Tah_4436"
    assert result.inis[0].data.iresd.loop_name == "Tah_6892"

    ofe2_ini_ref = result.man.ofeindx[1]
    assert ofe2_ini_ref.loop_name == "OFE2_Tah_2307"
    assert result.inis[1].data.iresd.loop_name == "OFE2_Tah_2823"

    ofe3_ini_ref = result.man.ofeindx[2]
    assert ofe3_ini_ref.loop_name == "OFE3_Shr_7020"
    assert result.inis[2].data.iresd.loop_name == "OFE3_Shr_6877"

    assert len(result.man.loops[0].years[0]) == 3

    ofe3_year_loop = result.man.loops[0].years[0][2]
    assert ofe3_year_loop.manindx[0].loop_name == "OFE3_Year 1"

    year_scenario_for_ofe3 = result.years[2]
    assert year_scenario_for_ofe3.data.itype.loop_name == "OFE3_Shr_6877"
