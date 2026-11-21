# SPDX-License-Identifier: GPL-2.0-or-later
"""Synthetic parser tests; no game dump, GPU or external packages required."""
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'scripts'))
from profile_renderer_v2 import profile_csv, render


class ProfileRendererV2Test(unittest.TestCase):
    def test_one_second_samples_and_nested_costs(self):
        with tempfile.TemporaryDirectory() as folder:
            csv = Path(folder) / 'renderer.csv'
            csv.write_text(
                'time_ns,interval_ms,flips,resources_ms,draw_ms,'
                'textures_ms,queue_reads,queue_fallbacks\n'
                '1,1000,10,20,80,10,1,0\n'
                '2,1000,10,20,80,10,1,0\n'
                '3,1000,20,40,100,30,4,2\n')
            profile = profile_csv(csv)
            self.assertEqual(profile['frames'], 20)
            self.assertEqual(profile['fps'], 20)
            self.assertEqual(profile['queue_reads'], 4)
            self.assertEqual(profile['queue_fallbacks'], 2)
            self.assertEqual(profile['phases'][0]['name'], 'draw')
            self.assertIn('nested categories may overlap', render(profile))

    def test_stall_sample_is_included_and_lightweight_mode_is_reported(self):
        with tempfile.TemporaryDirectory() as folder:
            csv = Path(folder) / 'renderer.csv'
            csv.write_text(
                'time_ns,interval_ms,flips,draw_ms,queue_reads,queue_fallbacks\n'
                '1,1000,10,0,0,0\n'
                '2,1000,10,0,0,0\n'
                '3,1000,0,0,0,0\n'
                '4,1000,20,0,3,1\n'
            )
            profile = profile_csv(csv)
            self.assertEqual(profile['samples'], 2)
            self.assertEqual(profile['frames'], 20)
            self.assertEqual(profile['fps'], 10.0)  # Includes the full second with no flips.
            self.assertFalse(profile['cpu_phases_recorded'])
            self.assertEqual(profile['slowest_windows'][0], (2.0, 0.0))
            self.assertEqual(profile['queue_reads'], 3)
            self.assertIn('low-impact mode', render(profile))
            self.assertIn('0.0 FPS', render(profile))

    def test_no_samples_and_bad_schema(self):
        with tempfile.TemporaryDirectory() as folder:
            csv = Path(folder) / 'renderer.csv'
            csv.write_text('interval_ms,flips\n1000,0\n')
            self.assertEqual(profile_csv(csv, skip=0)['samples'], 0)
            csv.write_text('wrong,header\n1,2\n')
            with self.assertRaises(ValueError):
                profile_csv(csv)


if __name__ == '__main__':
    unittest.main()
