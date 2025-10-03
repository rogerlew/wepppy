import unittest
from pathlib import Path

from wepppy.wepp.management.managements import read_management
from wepppy.wepp.management.utils.rotation_stack import ManagementRotationSynth


class TestManagementRotationSynth(unittest.TestCase):
    def test_stack_98_4_managements(self):
        base_dir = Path('/wc1/runs/du/dumbfounded-patentee/ag_fields/plant_files')
        man_paths = [
            base_dir / 'alfalfa,spr-seeded,NT,-cm8-wepp.man',
            base_dir / 'barley,spr,MT,-cm8,-fchisel-wepp.man',
        ]

        managements = [read_management(str(path)) for path in man_paths]
        synth = ManagementRotationSynth(managements)
        result = synth.build(key='stacked_alfalfa_barley')

        # Basic structure is preserved
        self.assertEqual(result.nofe, 1)
        self.assertEqual(result.man.nofes, 1)

        expected_years = sum(len(rot.years) for m in managements for rot in m.man.loops)
        self.assertEqual(result.sim_years, expected_years)
        self.assertEqual(result.man.loops[0].nyears, expected_years)
        self.assertEqual(len(result.man.loops), 1)

        # All section counts add up across the stacked segments
        self.assertEqual(len(result.plants), sum(len(m.plants) for m in managements))
        self.assertEqual(len(result.ops), sum(len(m.ops) for m in managements))
        self.assertEqual(len(result.inis), sum(len(m.inis) for m in managements))
        self.assertEqual(len(result.surfs), sum(len(m.surfs) for m in managements))
        self.assertEqual(len(result.years), sum(len(m.years) for m in managements))

        # Verify that segment two scenarios are prefixed and references updated
        plant_names = {loop.name for loop in result.plants}
        self.assertIn('SEG2_L165_Whea', plant_names)
        self.assertIn('SEG2_L179_weed', plant_names)

        year_names = {loop.name for loop in result.years}
        self.assertIn('SEG2_Year 1', year_names)
        seg2_year = next(loop for loop in result.years if loop.name == 'SEG2_Year 1')
        self.assertEqual(seg2_year.data.itype.loop_name, 'SEG2_L165_Whea')
        self.assertEqual(seg2_year.data.tilseq.loop_name, 'SEG2_Year 1')

        # Timeline order: first management's years, then the prefixed second management
        timeline = []
        for per_ofe in result.man.loops[0].years:
            man_loop = per_ofe[0]
            timeline.extend(ref.loop_name for ref in man_loop.manindx)

        first_segment_years = sum(len(rot.years) for rot in managements[0].man.loops)
        self.assertEqual(len(timeline), expected_years)
        self.assertTrue(all(not name.startswith('SEG2_') for name in timeline[:first_segment_years]))
        self.assertTrue(all(name.startswith('SEG2_') for name in timeline[first_segment_years:]))


if __name__ == '__main__':
    unittest.main()
