# SPDX-License-Identifier: GPL-2.0-or-later
"""Launcher settings must not discard saved graphics options."""
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from launcher.fl_launcher.settings import (CORE_DEFAULTS, RENDER_RESOLUTIONS, Settings,
                                           consume_ini_switches)


class LauncherGraphicsSettingsTest(unittest.TestCase):
    def test_new_install_defaults(self):
        with tempfile.TemporaryDirectory() as folder:
            core = Settings(folder).core
            self.assertEqual((core['fsr1'], core['rcas']), ('1', '1'))
            self.assertEqual((core['async_shaders'], core['stale_readback']), ('0', '0'))
            self.assertEqual(core['deferred_readback'], '1')

    def test_high_detail_and_performance_resolutions_are_selectable(self):
        self.assertEqual(RENDER_RESOLUTIONS[0], 'native')
        for resolution in ('1440p', '1800p', '4K', '800p', '720p'):
            self.assertIn(resolution, RENDER_RESOLUTIONS)

    def test_existing_values_not_overwritten(self):
        with tempfile.TemporaryDirectory() as folder:
            (Path(folder) / 'tlg.ini').write_text(
                'fsr1=0\nrcas=0\nasync_shaders=1\nstale_readback=1\n'
                'deferred_readback=0\n', encoding='utf-8')
            settings = Settings(folder)
            extra = {'TLG_FRAME_STATS': '1'}
            consume_ini_switches(settings.core, extra)
            self.assertEqual(extra, {'TLG_FRAME_STATS': '1'})
            self.assertEqual((settings.core['fsr1'], settings.core['rcas']), ('0', '0'))
            self.assertEqual(settings.core['async_shaders'], '1')
            self.assertEqual((settings.core['stale_readback'],
                              settings.core['deferred_readback']), ('1', '0'))
            settings.save()
            self.assertEqual(Settings(folder).core['deferred_readback'], '0')

    def test_explicit_advanced_env_only(self):
        core = dict(CORE_DEFAULTS, deferred_readback='0', stale_readback='1')
        extra = {'TLG_STALE_READBACK': '0', 'TLG_UPSCALER': 'fsr3'}
        consume_ini_switches(core, extra)
        self.assertEqual((core['deferred_readback'], core['stale_readback']), ('0', '0'))
        self.assertEqual(extra, {'TLG_UPSCALER': 'fsr3'})


if __name__ == '__main__':
    unittest.main()
