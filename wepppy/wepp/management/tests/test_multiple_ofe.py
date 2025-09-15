import unittest
import os
import tempfile
from copy import deepcopy

# Assuming the provided classes are in wepppy.wepp.management
# Add the path to your wepppy project if it's not in the PYTHONPATH
# import sys
# sys.path.append('/path/to/your/wepppy/project')
from wepppy.wepp.management import Management, read_management
from wepppy.wepp.management.utils import ManagementMultipleOfeSynth

# --- Test Data ---

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


class TestManagementMultipleOfeSynth(unittest.TestCase):
    """
    Test suite for the ManagementMultipleOfeSynth class.
    """
    def test_synthesis_of_three_ofes(self):
        """
        Tests the synthesis of three different management files into a single
        file representing a 3-OFE hillslope.
        """
        with tempfile.TemporaryDirectory() as temp_dir:
            # Arrange: Write the input files and load them
            man1_path = os.path.join(temp_dir, 'high_sev.man')
            man2_path = os.path.join(temp_dir, 'low_sev.man')
            man3_path = os.path.join(temp_dir, 'shrub.man')
            output_path = os.path.join(temp_dir, 'synthesized.man')

            with open(man1_path, 'w') as f: f.write(HIGH_SEVERITY_FIRE_MAN)
            with open(man2_path, 'w') as f: f.write(LOW_SEVERITY_FIRE_MAN)
            with open(man3_path, 'w') as f: f.write(SHRUB_MAN)

            man1 = read_management(man1_path)
            man2 = read_management(man2_path)
            man3 = read_management(man3_path)

            stack = [man1, man2, man3]
            synth = ManagementMultipleOfeSynth(stack=stack)

            # Act: Run the synthesis process
            synth.write(output_path)

            # Assert: Verify the contents of the synthesized file
            self.assertTrue(os.path.exists(output_path))
            result_man = read_management(output_path)

            # 1. Check top-level properties
            self.assertEqual(result_man.nofe, 3)
            self.assertEqual(result_man.man.nofes, 3)

            # 2. Check counts in each section
            self.assertEqual(len(result_man.plants), 3)
            self.assertEqual(len(result_man.ops), 0)
            self.assertEqual(len(result_man.inis), 3)
            self.assertEqual(len(result_man.years), 3)

            # 3. Check for unique, prefixed scenario names
            self.assertEqual(result_man.plants[0].name, 'Tah_6892')
            self.assertEqual(result_man.plants[1].name, 'OFE2_Tah_2823')
            self.assertEqual(result_man.plants[2].name, 'OFE3_Shr_6877')
            
            self.assertEqual(result_man.inis[0].name, 'Tah_4436')
            self.assertEqual(result_man.inis[1].name, 'OFE2_Tah_2307')
            self.assertEqual(result_man.inis[2].name, 'OFE3_Shr_7020')

            self.assertEqual(result_man.years[0].name, 'Year 1')
            self.assertEqual(result_man.years[1].name, 'OFE2_Year 1')
            self.assertEqual(result_man.years[2].name, 'OFE3_Year 1')

            # 4. Check critical references to ensure they were updated correctly
            # OFE 1 (the base case)
            ofe1_ini_ref = result_man.man.ofeindx[0]
            self.assertEqual(ofe1_ini_ref.loop_name, 'Tah_4436')
            self.assertEqual(result_man.inis[0].data.iresd.loop_name, 'Tah_6892')  # plant reference

            # OFE 2
            ofe2_ini_ref = result_man.man.ofeindx[1]
            self.assertEqual(ofe2_ini_ref.loop_name, 'OFE2_Tah_2307')
            self.assertEqual(result_man.inis[1].data.iresd.loop_name, 'OFE2_Tah_2823')  # plant reference

            # OFE 3
            ofe3_ini_ref = result_man.man.ofeindx[2]
            self.assertEqual(ofe3_ini_ref.loop_name, 'OFE3_Shr_7020')
            self.assertEqual(result_man.inis[2].data.iresd.loop_name, 'OFE3_Shr_6877')  # plant reference

            # 5. Check the final management loops
            self.assertEqual(len(result_man.man.loops[0].years[0]), 3, "Should be 3 OFEs defined for year 1")
            
            # Check yearly reference for OFE 3
            ofe3_year_man_loop = result_man.man.loops[0].years[0][2]
            self.assertEqual(ofe3_year_man_loop.manindx[0].loop_name, 'OFE3_Year 1')

            # 6. Check that the yearly scenario for OFE 3 points to the correct plant
            year_scenario_for_ofe3 = result_man.years[2] # This is 'OFE3_Year 1'
            self.assertEqual(year_scenario_for_ofe3.data.itype.loop_name, 'OFE3_Shr_6877')


if __name__ == '__main__':
    unittest.main()