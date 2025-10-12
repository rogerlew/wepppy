from pathlib import Path
import unittest

from wepppy.wepp.management import (
    _management_dir,
    get_disturbed_classes,
    get_management_summary,
    load_map,
    InvalidManagementKey,
    ManagementSummary,
)


EXPECTED_DISTURBED_CLASSES = {
    None,
    "agriculture crops",
    "bare",
    "developed high intensity",
    "developed low intensity",
    "developed moderate intensity",
    "forest",
    "forest high sev fire",
    "forest low sev fire",
    "forest moderate sev fire",
    "forest prescribed fire",
    "grass high sev fire",
    "grass low sev fire",
    "grass moderate sev fire",
    "grass prescribed fire",
    "mulch",
    "mulch_15",
    "mulch_30",
    "mulch_60",
    "prescribed_fire",
    "short grass",
    "shrub",
    "shrub high sev fire",
    "shrub low sev fire",
    "shrub moderate sev fire",
    "shrub prescribed fire",
    "skid",
    "tall grass",
    "thinning_40_75",
    "thinning_40_85",
    "thinning_40_90",
    "thinning_40_93",
    "thinning_65_75",
    "thinning_65_85",
    "thinning_65_90",
    "thinning_65_93",
    "young forest",
}


class TestGetDisturbedClasses(unittest.TestCase):
    def test_disturbed_classes_snapshot(self):
        classes = get_disturbed_classes()
        self.assertEqual(classes, EXPECTED_DISTURBED_CLASSES)
        self.assertEqual(len(classes), 37)


class TestLoadMap(unittest.TestCase):
    def test_default_map_contains_known_entry(self):
        data = load_map()
        self.assertIn("21", data)
        entry = data["21"]
        self.assertEqual(entry["Description"], "Low Intensity Residential")
        self.assertEqual(entry["ManagementFile"], "GeoWEPP/grass.man")
        self.assertNotIn("1", data)  # sanity check for eu-specific keys

    def test_routes_specialized_maps(self):
        cases = {
            "eu-disturbed": ("1", "Continuous urban fabric"),
            "c3s-disturbed": ("10", "crops, rainfed"),
            "revegetation": ("41", "Deciduous Forest"),
        }
        for map_name, (key, expected_desc) in cases.items():
            with self.subTest(map_name=map_name):
                data = load_map(map_name)
                self.assertIn(key, data)
                self.assertEqual(data[key]["Description"], expected_desc)

    def test_unknown_map_falls_back_to_default(self):
        default = load_map()
        other = load_map("this-map-does-not-exist")
        self.assertEqual(default["21"]["Description"], other["21"]["Description"])


class TestGetManagementSummary(unittest.TestCase):
    def test_default_management_summary(self):
        summary = get_management_summary(21)
        expected_path = Path(_management_dir) / "GeoWEPP/grass.man"
        self.assertEqual(summary.key, 21)
        self.assertEqual(summary.disturbed_class, "")
        self.assertIsNone(summary.sol_path)
        self.assertEqual(Path(summary.man_path), expected_path)
        self.assertTrue(expected_path.exists())
        self.assertEqual(summary.color, "#ddc9c9")
        self.assertEqual(summary.get_management().man_fn, "GeoWEPP/grass.man")

    def test_disturbed_map_summary_contains_disturbance_metadata(self):
        summary = get_management_summary(21, _map="disturbed")
        man_path = Path(_management_dir) / "UnDisturbed/Developed_Low_Intensity.man"
        sol_path = Path(_management_dir) / "UnDisturbed/Developed_Low_Intensity.sol"
        self.assertEqual(summary.disturbed_class, "developed low intensity")
        self.assertEqual(Path(summary.man_path), man_path)
        self.assertEqual(Path(summary.sol_path), sol_path)
        self.assertEqual(summary.get_management().man_fn, "UnDisturbed/Developed_Low_Intensity.man")

    def test_eu_disturbed_summary_uses_variant_map(self):
        summary = get_management_summary(1, _map="eu-disturbed")
        self.assertEqual(summary.key, 1)
        self.assertEqual(summary.disturbed_class, "developed high intensity")
        self.assertTrue(Path(summary.man_path).name.endswith("Developed_High_Intensity.man"))
        self.assertTrue(Path(summary.sol_path).name.endswith("Developed_High_Intensity.sol"))
        self.assertIn(summary.disturbed_class, get_disturbed_classes())

    def test_invalid_key_raises(self):
        with self.assertRaises(InvalidManagementKey):
            get_management_summary(999999)

    def test_invalid_disturbed_class_raises(self):
        disturbed_map = load_map("disturbed")
        invalid_record = dict(disturbed_map["21"])
        invalid_record["DisturbedClass"] = "definitely-not-valid"
        with self.assertRaises(ValueError):
            ManagementSummary(**invalid_record, _map="disturbed")


if __name__ == "__main__":
    unittest.main()
