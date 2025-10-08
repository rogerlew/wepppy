import unittest
from pathlib import Path

from wepppy.wepp.management.managements import read_management
from wepppy.wepp.management.utils.rotation_stack import ManagementRotationSynth


class TestManagementRotationSynth(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tests_dir = Path(__file__).resolve().parent
        cls.data_dir = cls.tests_dir.parent / 'data'
        cls.ag_dir = cls.data_dir / 'Agriculture'

    def _load(self, relative_path: str):
        return read_management(str(self.ag_dir / relative_path))

    def test_stack_end_to_end_managements(self):
        managements = [
            self._load('corn,soybean-no till.man'),
            self._load('corn,soybean-fall moldboard plow.man'),
        ]

        synth = ManagementRotationSynth(managements)
        result = synth.build(key='stacked_rotation')

        self.assertEqual(result.nofe, 1)
        self.assertEqual(result.man.nofes, 1)

        expected_years = sum(len(rot.years) for m in managements for rot in m.man.loops)
        self.assertEqual(result.sim_years, expected_years)
        self.assertEqual(result.man.loops[0].nyears, expected_years)
        self.assertEqual(len(result.man.loops), 1)

        # Section counts add up across stacked segments
        self.assertEqual(len(result.plants), sum(len(m.plants) for m in managements))
        self.assertEqual(len(result.ops), sum(len(m.ops) for m in managements))
        self.assertEqual(len(result.inis), sum(len(m.inis) for m in managements))
        self.assertEqual(len(result.surfs), sum(len(m.surfs) for m in managements))
        self.assertEqual(len(result.years), sum(len(m.years) for m in managements))

        # Verify prefixed names for the second segment
        for loop in managements[1].plants:
            self.assertIn(f"SEG2_{loop.name}", {p.name for p in result.plants})

        for loop in managements[1].years:
            self.assertIn(f"SEG2_{loop.name}", {y.name for y in result.years})

        timeline = []
        for per_ofe in result.man.loops[0].years:
            man_loop = per_ofe[0]
            timeline.extend(ref.loop_name for ref in man_loop.manindx if ref.loop_name)

        first_segment_years = sum(len(rot.years) for rot in managements[0].man.loops)
        self.assertEqual(len(timeline), expected_years)
        self.assertTrue(all(not name.startswith('SEG2_') for name in timeline[:first_segment_years]))
        self.assertTrue(all(name.startswith('SEG2_') for name in timeline[first_segment_years:]))

    def test_stack_and_merge_drops_first_year(self):
        two_year = self._load('corn,soybean-fall moldboard plow.man')

        synth = ManagementRotationSynth([two_year], mode='stack-and-merge')
        result = synth.build(key='stack_and_merge_single')

        # First year discarded; only a single year remains
        self.assertEqual(result.sim_years, 1)
        self.assertEqual(result.man.loops[0].nyears, 1)
        year_names = [loop.name for loop in result.years]
        self.assertNotIn('Year 1', year_names)
        self.assertEqual(len(year_names), 1)
        self.assertFalse(synth.warnings)

    def test_stack_and_merge_merges_operations(self):
        first = self._load('corn,soybean-fall moldboard plow.man')
        second = self._load('corn,soybean-fall moldboard plow.man')

        second_year_ref = next(
            ref.loop_name
            for ref in first.man.loops[0].years[1][0].manindx
            if ref.loop_name
        )
        original_second_year_loop = next(loop for loop in first.years if loop.name == second_year_ref)
        original_surf_name = original_second_year_loop.data.tilseq.loop_name
        original_surf = next(loop for loop in first.surfs if loop.name == original_surf_name)
        original_operation_count = len(original_surf.data)

        synth = ManagementRotationSynth([first, second], mode='stack-and-merge')
        result = synth.build(key='stack_and_merge_double')

        self.assertEqual(result.sim_years, 2)
        self.assertEqual(result.man.loops[0].nyears, 2)
        self.assertTrue(synth.warnings)
        self.assertTrue(
            all('occurs before day' in msg for msg in synth.warnings),
            synth.warnings,
        )

        first_year_ref = next(
            ref.loop_name
            for ref in result.man.loops[0].years[0][0].manindx
            if ref.loop_name
        )
        year_lookup = {loop.name: loop for loop in result.years}
        first_year = year_lookup[first_year_ref]
        surf_name = first_year.data.tilseq.loop_name
        surf_loop = next(loop for loop in result.surfs if loop.name == surf_name)
        self.assertEqual(surf_loop.ntill, len(surf_loop.data))

        # First-year operations from the second segment should be appended.
        self.assertGreater(len(surf_loop.data), original_operation_count)

    def test_stack_and_merge_emits_warnings_for_out_of_order_operations(self):
        base = self._load('corn,soybean-fall moldboard plow.man')
        modified = self._load('corn,soybean-fall moldboard plow.man')

        # Force a late operation to become early, triggering a warning during merge
        rotation = modified.man.loops[0]
        first_year_name = next(
            ref.loop_name
            for ref in rotation.years[0][0].manindx
            if ref.loop_name
        )
        first_year_loop = next(loop for loop in modified.years if loop.name == first_year_name)
        surf_name = first_year_loop.data.tilseq.loop_name
        surf_loop = next(loop for loop in modified.surfs if loop.name == surf_name)
        for op in surf_loop.data:
            op.mdate = 1  # Move to day 1 to ensure out-of-order merge

        synth = ManagementRotationSynth([base, modified], mode='stack-and-merge')
        result = synth.build(key='stack_and_merge_warning')
        self.assertEqual(result.sim_years, 2)
        self.assertTrue(synth.warnings)


if __name__ == '__main__':
    unittest.main()
