"""
Disturbed WEPP Test Matrix

Runs the full matrix of:
- 4 soil textures (clay loam, loam, sand loam, silt loam)
- 4 burn severities (unburned, low, moderate, high)
- 3 vegetation types (forest, shrub, tall grass)

Total: 48 hillslope simulations using 9002 soil format.

This test exercises the Disturbed module's soil modification workflow
using the disturbed_land_soil_lookup.csv for parameter replacements.
"""

import csv
import itertools
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

import pytest

# Import wepppy modules (avoiding nodb imports that require rosetta)
from wepppy.wepp.soils.utils import WeppSoilUtil
from wepppy.wepp.management import Management

# Import wepp_runner
from wepp_runner import run_hillslope, make_hillslope_run


# =============================================================================
# Local implementation of read_disturbed_land_soil_lookup
# (Avoids importing from wepppy.nodb which has rosetta dependencies)
# =============================================================================


def read_disturbed_land_soil_lookup(fname: str) -> Dict[Tuple[str, str], Dict[str, Any]]:
    """
    Read the disturbed land-soil lookup CSV file.

    Args:
        fname: Path to the CSV file.

    Returns:
        Dictionary keyed by (texture, disturbed_class) with parameter values.
    """
    d: Dict[Tuple[str, str], Dict[str, Any]] = {}

    with open(fname) as fp:
        reader = csv.DictReader(fp)
        for row in reader:
            # Handle column name variations
            try:
                disturbed_class = row["luse"]
            except KeyError:
                disturbed_class = row["disturbed_class"]

            try:
                texid = row["stext"]
            except KeyError:
                texid = row["texid"]

            # Convert 'none*' strings to None
            for k in row:
                v = row[k]
                if isinstance(v, str):
                    if v.lower().startswith("none"):
                        row[k] = None

            if texid != "" and disturbed_class != "":
                if texid == "all":
                    d[("clay loam", disturbed_class)] = row
                    d[("loam", disturbed_class)] = row
                    d[("sand loam", disturbed_class)] = row
                    d[("silt loam", disturbed_class)] = row
                else:
                    d[(texid, disturbed_class)] = row

    return d


# =============================================================================
# Test Configuration
# =============================================================================

# Soil textures (from simple_texture())
TEXTURES = ["clay loam", "loam", "sand loam", "silt loam"]

# Burn severities: 0=unburned, 1=low, 2=moderate, 3=high
SEVERITIES = [0, 1, 2, 3]
SEVERITY_NAMES = {0: "unburned", 1: "low", 2: "moderate", 3: "high"}

# Vegetation types
VEG_TYPES = ["forest", "shrub", "tall grass"]

# Simulation years (must match climate file)
SIM_YEARS = 100

# Canonical soil files for each texture
CANONICAL_SOILS = {
    "clay loam": "Forest clay loam.sol",
    "loam": "Forest loam.sol",
    "sand loam": "Forest sandy loam.sol",
    "silt loam": "Forest silt loam.sol",
}

# Management files for each (veg_type, severity) combination
MANAGEMENT_FILES = {
    # Unburned (severity=0)
    ("forest", 0): "UnDisturbed/Old_Forest.man",
    ("shrub", 0): "UnDisturbed/Shrub.man",
    ("tall grass", 0): "UnDisturbed/Tall_Grass.man",
    # Low severity (severity=1)
    ("forest", 1): "UnDisturbed/Low_Severity_Fire.man",
    ("shrub", 1): "UnDisturbed/Shrub_Low_Severity_Fire.man",
    ("tall grass", 1): "UnDisturbed/Grass_Low_Severity_Fire.man",
    # Moderate severity (severity=2)
    ("forest", 2): "UnDisturbed/Moderate_Severity_Fire.man",
    ("shrub", 2): "UnDisturbed/Shrub_Moderate_Severity_Fire.man",
    ("tall grass", 2): "UnDisturbed/Grass_Moderate_Severity_Fire.man",
    # High severity (severity=3)
    ("forest", 3): "UnDisturbed/High_Severity_Fire.man",
    ("shrub", 3): "UnDisturbed/Shrub_High_Severity_Fire.man",
    ("tall grass", 3): "UnDisturbed/Grass_High_Severity_Fire.man",
}

# Disturbed class names for each (veg_type, severity) combination
DISTURBED_CLASSES = {
    # Unburned
    ("forest", 0): "forest",
    ("shrub", 0): "shrub",
    ("tall grass", 0): "tall grass",
    # Low severity
    ("forest", 1): "forest low sev fire",
    ("shrub", 1): "shrub low sev fire",
    ("tall grass", 1): "grass low sev fire",
    # Moderate severity
    ("forest", 2): "forest moderate sev fire",
    ("shrub", 2): "shrub moderate sev fire",
    ("tall grass", 2): "grass moderate sev fire",
    # High severity
    ("forest", 3): "forest high sev fire",
    ("shrub", 3): "shrub high sev fire",
    ("tall grass", 3): "grass high sev fire",
}


# =============================================================================
# Data Classes
# =============================================================================


@dataclass
class HillslopeResult:
    """Container for a single hillslope simulation result."""

    wepp_id: int
    texture: str
    severity: int
    veg_type: str
    disturbed_class: str
    success: bool
    elapsed_time: float
    error_message: Optional[str] = None


# =============================================================================
# Helper Functions
# =============================================================================


def create_run_file(wepp_id: int, sim_years: int, runs_dir: Path) -> None:
    """Create a WEPP .run file using the standard reveg template (has graphics enabled)."""
    make_hillslope_run(
        wepp_id=wepp_id,
        sim_years=sim_years,
        runs_dir=str(runs_dir),
        reveg=True,  # Uses reveg_hillslope.template which has graphical output enabled
    )


def prepare_slope(
    wepp_id: int, canonical_slope_path: Path, runs_dir: Path
) -> None:
    """Copy the canonical slope file for this hillslope."""
    dst = runs_dir / f"p{wepp_id}.slp"
    shutil.copy(canonical_slope_path, dst)


def prepare_climate(
    wepp_id: int, test_climate_path: Path, runs_dir: Path
) -> None:
    """Copy the test climate file for this hillslope."""
    dst = runs_dir / f"p{wepp_id}.cli"
    shutil.copy(test_climate_path, dst)


def prepare_management(
    wepp_id: int,
    veg_type: str,
    severity: int,
    management_data_dir: Path,
    runs_dir: Path,
    sim_years: int,
) -> None:
    """Prepare the management file for this hillslope."""
    man_relpath = MANAGEMENT_FILES[(veg_type, severity)]

    # Parse the relative path to get directory and filename
    parts = man_relpath.split("/")
    man_fn = parts[-1]  # e.g., "Old_Forest.man"
    man_subdir = "/".join(parts[:-1]) if len(parts) > 1 else ""  # e.g., "UnDisturbed"
    man_dir = str(management_data_dir / man_subdir) if man_subdir else str(management_data_dir)

    # Load management using the correct API
    man = Management.load(
        key=None,
        man_fn=man_fn,
        man_dir=man_dir,
        desc=f"{veg_type} {SEVERITY_NAMES[severity]}",
    )
    multi_year = man.build_multiple_year_man(sim_years=sim_years)

    dst = runs_dir / f"p{wepp_id}.man"
    with open(dst, "w") as fp:
        fp.write(str(multi_year))


def prepare_soil_9002(
    wepp_id: int,
    texture: str,
    veg_type: str,
    severity: int,
    forest_soils_dir: Path,
    lookup_d: Dict[Tuple[str, str], Dict[str, Any]],
    runs_dir: Path,
) -> None:
    """Generate a 9002 format disturbed soil file."""
    # Load the base soil for this texture
    base_soil_path = forest_soils_dir / CANONICAL_SOILS[texture]
    soil_u = WeppSoilUtil(str(base_soil_path))

    # Get the disturbed class for lookup
    disturbed_class = DISTURBED_CLASSES[(veg_type, severity)]

    # Get replacements from lookup table
    key = (texture, disturbed_class)
    replacements = lookup_d.get(key, {}).copy()

    # Add 9002-specific metadata
    replacements["luse"] = disturbed_class
    replacements["stext"] = texture

    # Generate 9002 disturbed soil
    disturbed_soil = soil_u.to_over9000(
        replacements=replacements,
        h0_max_om=None,
        version=9002,
    )

    # Write to destination
    dst = runs_dir / f"p{wepp_id}.sol"
    disturbed_soil.write(str(dst))


def generate_wepp_id(texture: str, severity: int, veg_type: str) -> int:
    """Generate a unique WEPP ID for this combination."""
    texture_idx = TEXTURES.index(texture)
    veg_idx = VEG_TYPES.index(veg_type)
    # wepp_id = texture * 12 + veg * 4 + severity + 1 (1-indexed)
    return texture_idx * 12 + veg_idx * 4 + severity + 1


# =============================================================================
# Test Class
# =============================================================================


class TestDisturbedMatrix:
    """Test class for the disturbed parameter matrix."""

    @pytest.fixture(scope="class")
    def lookup_d(self, disturbed_lookup_path: Path) -> Dict[Tuple[str, str], Dict[str, Any]]:
        """Load the disturbed land-soil lookup table."""
        return read_disturbed_land_soil_lookup(str(disturbed_lookup_path))

    @pytest.fixture(scope="class")
    def all_results(self) -> Dict[Tuple[str, int, str], HillslopeResult]:
        """Shared storage for all test results."""
        return {}

    @pytest.mark.parametrize(
        "texture,severity,veg_type",
        list(itertools.product(TEXTURES, SEVERITIES, VEG_TYPES)),
        ids=lambda x: str(x) if not isinstance(x, tuple) else f"{x[0]}-{SEVERITY_NAMES.get(x[1], x[1])}-{x[2]}".replace(" ", "_"),
    )
    def test_hillslope_simulation(
        self,
        texture: str,
        severity: int,
        veg_type: str,
        runs_dir: Path,
        output_dir: Path,
        canonical_slope_path: Path,
        test_climate_path: Path,
        forest_soils_dir: Path,
        management_data_dir: Path,
        lookup_d: Dict[Tuple[str, str], Dict[str, Any]],
        all_results: Dict[Tuple[str, int, str], HillslopeResult],
    ):
        """Test a single texture/severity/veg combination."""
        wepp_id = generate_wepp_id(texture, severity, veg_type)
        disturbed_class = DISTURBED_CLASSES[(veg_type, severity)]

        # 1. Prepare slope file
        prepare_slope(wepp_id, canonical_slope_path, runs_dir)

        # 2. Prepare climate file
        prepare_climate(wepp_id, test_climate_path, runs_dir)

        # 3. Prepare management file
        prepare_management(
            wepp_id, veg_type, severity, management_data_dir, runs_dir, SIM_YEARS
        )

        # 4. Generate 9002 disturbed soil
        prepare_soil_9002(
            wepp_id, texture, veg_type, severity, forest_soils_dir, lookup_d, runs_dir
        )

        # 5. Create .run file using standard reveg template (has graphics enabled)
        create_run_file(wepp_id, SIM_YEARS, runs_dir)

        # 6. Run WEPP
        try:
            success, returned_id, elapsed = run_hillslope(
                wepp_id=wepp_id,
                runs_dir=str(runs_dir),
                wepp_bin="latest",
                timeout=300,  # 5 minutes for 100-year simulation
            )
            result = HillslopeResult(
                wepp_id=wepp_id,
                texture=texture,
                severity=severity,
                veg_type=veg_type,
                disturbed_class=disturbed_class,
                success=success,
                elapsed_time=elapsed,
            )
        except Exception as e:
            result = HillslopeResult(
                wepp_id=wepp_id,
                texture=texture,
                severity=severity,
                veg_type=veg_type,
                disturbed_class=disturbed_class,
                success=False,
                elapsed_time=0.0,
                error_message=str(e),
            )

        # Store result for later analysis
        all_results[(texture, severity, veg_type)] = result

        # Assertions
        assert result.success, (
            f"WEPP failed for {texture}/{SEVERITY_NAMES[severity]}/{veg_type}: "
            f"{result.error_message or 'see error log'}"
        )

        # Verify output files were created
        pass_file = output_dir / f"H{wepp_id}.pass.dat"
        assert pass_file.exists(), f"Pass file not created: {pass_file}"

        graph_file = output_dir / f"H{wepp_id}.grph.dat"
        assert graph_file.exists(), f"Graph file not created: {graph_file}"

    def test_severity_gradient_forest(
        self,
        all_results: Dict[Tuple[str, int, str], HillslopeResult],
    ):
        """Verify all forest simulations completed successfully."""
        forest_results = [
            r for (t, s, v), r in all_results.items() if v == "forest"
        ]
        if not forest_results:
            pytest.skip("No forest results available yet")

        failed = [r for r in forest_results if not r.success]
        assert not failed, f"Failed forest simulations: {failed}"

    def test_severity_gradient_shrub(
        self,
        all_results: Dict[Tuple[str, int, str], HillslopeResult],
    ):
        """Verify all shrub simulations completed successfully."""
        shrub_results = [
            r for (t, s, v), r in all_results.items() if v == "shrub"
        ]
        if not shrub_results:
            pytest.skip("No shrub results available yet")

        failed = [r for r in shrub_results if not r.success]
        assert not failed, f"Failed shrub simulations: {failed}"

    def test_severity_gradient_grass(
        self,
        all_results: Dict[Tuple[str, int, str], HillslopeResult],
    ):
        """Verify all tall grass simulations completed successfully."""
        grass_results = [
            r for (t, s, v), r in all_results.items() if v == "tall grass"
        ]
        if not grass_results:
            pytest.skip("No tall grass results available yet")

        failed = [r for r in grass_results if not r.success]
        assert not failed, f"Failed tall grass simulations: {failed}"


# =============================================================================
# Standalone Execution
# =============================================================================

if __name__ == "__main__":
    # Allow running as standalone script for debugging
    import sys
    import tempfile

    print("Running disturbed matrix test...")
    print(f"Textures: {TEXTURES}")
    print(f"Severities: {list(SEVERITY_NAMES.values())}")
    print(f"Veg types: {VEG_TYPES}")
    print(f"Total combinations: {len(TEXTURES) * len(SEVERITIES) * len(VEG_TYPES)}")

    # Run with pytest
    sys.exit(pytest.main([__file__, "-v", "--tb=short"]))
