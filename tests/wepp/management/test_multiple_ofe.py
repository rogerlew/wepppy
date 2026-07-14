from __future__ import annotations

from copy import deepcopy
from pathlib import Path

import pytest

from wepppy.wepp.management import read_management
from wepppy.wepp.management.utils import ManagementMultipleOfeSynth

MOFE_NSCEN_OVERFLOW_FIXTURE_DIR = (
    Path(__file__).resolve().parent / "fixtures" / "mofe_nscen_overflow"
)


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


def _referenced_yearly_names(management) -> list[str]:
    names: list[str] = []
    seen = set()
    for rotation in management.man.loops:
        for year in rotation.years:
            for ofe in year:
                for year_ref in ofe.manindx:
                    if year_ref.loop_name is None or year_ref.loop_name in seen:
                        continue
                    seen.add(year_ref.loop_name)
                    names.append(year_ref.loop_name)
    return names


def _orphan_yearly_names(management) -> list[str]:
    referenced = set(_referenced_yearly_names(management))
    return [year_loop.name for year_loop in management.years if year_loop.name not in referenced]


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
    assert output_path.read_text().splitlines()[0] == "98.4"

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


@pytest.mark.unit
@pytest.mark.parametrize(
    ("fixture_rel_path", "expected_nscen", "expected_orphans"),
    [
        (
            Path("patrician-ambivalence/p386.man"),
            21,
            ["OFE10_Year 2", "OFE11_Year 2"],
        ),
        (
            Path("congealed-inspector/p1802.man"),
            25,
            [
                "OFE3_Year 2",
                "OFE4_Year 2",
                "OFE5_Year 2",
                "OFE6_Year 2",
                "OFE7_Year 2",
                "OFE8_Year 2",
            ],
        ),
    ],
)
def test_mofe_fixture_compaction_culls_orphan_yearly_scenarios(
    tmp_path: Path,
    fixture_rel_path: Path,
    expected_nscen: int,
    expected_orphans: list[str],
) -> None:
    fixture_path = MOFE_NSCEN_OVERFLOW_FIXTURE_DIR / fixture_rel_path
    management = read_management(str(fixture_path))

    assert management.nofe == 19
    assert management.nscen == expected_nscen
    assert _orphan_yearly_names(management) == expected_orphans

    ManagementMultipleOfeSynth._compact_yearly_scenarios(management)

    expected_referenced_years = ["Year 1"] + [f"OFE{i}_Year 1" for i in range(2, 20)]
    assert _referenced_yearly_names(management) == expected_referenced_years
    assert [year_loop.name for year_loop in management.years] == expected_referenced_years
    assert _orphan_yearly_names(management) == []
    assert management.nscen == 19

    compacted_path = tmp_path / f"compacted_{fixture_path.name}"
    compacted_path.write_text(str(management))
    reparsed = read_management(str(compacted_path))

    assert reparsed.nscen == 19
    assert _orphan_yearly_names(reparsed) == []


@pytest.mark.unit
def test_mofe_synth_compacts_orphan_yearly_scenarios(tmp_path: Path) -> None:
    man_paths = [
        _write_management(tmp_path, "high.man", HIGH_SEVERITY_FIRE_MAN),
        _write_management(tmp_path, "low.man", LOW_SEVERITY_FIRE_MAN),
    ]

    stack = [read_management(str(path)) for path in man_paths]
    stack[1].years.append(deepcopy(stack[1].years[0]))
    stack[1].years[-1].name = "Year 2"

    synth = ManagementMultipleOfeSynth(stack=stack)
    output_path = tmp_path / "synthesized_compacted.man"
    synth.write(str(output_path))

    result = read_management(str(output_path))
    assert result.nscen == 2
    assert [year_loop.name for year_loop in result.years] == ["Year 1", "OFE2_Year 1"]
    assert _referenced_yearly_names(result) == ["Year 1", "OFE2_Year 1"]
    assert _orphan_yearly_names(result) == []


@pytest.mark.unit
def test_mofe_synth_raises_when_referenced_yearly_scenarios_exceed_hillslope_limit(
    tmp_path: Path,
) -> None:
    man_paths = [
        _write_management(tmp_path, f"man_{i}.man", HIGH_SEVERITY_FIRE_MAN)
        for i in range(21)
    ]
    stack = [read_management(str(path)) for path in man_paths]
    synth = ManagementMultipleOfeSynth(stack=stack)

    with pytest.raises(ValueError) as exc_info:
        synth.write(str(tmp_path / "overflow.man"))

    message = str(exc_info.value)
    assert "21 referenced yearly scenarios" in message
    assert "WEPP hillslope limit of 20" in message
    assert "nmscen must be between 1 and 20" in message


@pytest.mark.unit
def test_mofe_synth_can_deduplicate_equivalent_scenario_graphs(tmp_path: Path) -> None:
    man_paths = [
        _write_management(tmp_path, f"man_{i}.man", HIGH_SEVERITY_FIRE_MAN)
        for i in range(3)
    ]
    stack = [read_management(str(path)) for path in man_paths]
    synth = ManagementMultipleOfeSynth(stack=stack, deduplicate_scenarios=True)

    output_path = tmp_path / "deduplicated.man"
    synth.write(str(output_path))

    result = read_management(str(output_path))
    assert result.nofe == result.man.nofes == 3
    assert len(result.plants) == 1
    assert len(result.inis) == 1
    assert len(result.years) == 1
    assert [reference.loop_name for reference in result.man.ofeindx] == [
        "Tah_4436",
        "Tah_4436",
        "Tah_4436",
    ]
    assert all(
        ofe.manindx[0].loop_name == "Year 1"
        for ofe in result.man.loops[0].years[0]
    )
