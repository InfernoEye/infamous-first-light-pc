# SPDX-License-Identifier: GPL-2.0-or-later
"""One-click report includes only safe, bounded numeric renderer profiles."""
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from launcher.fl_launcher import report


class RendererReportProfileTest(unittest.TestCase):
    @staticmethod
    def create_csv(folder, stamp, body="0,1000,15,12.5\n"):
        directory = Path(folder) / "profiling"
        directory.mkdir(exist_ok=True)
        path = directory / f"renderer-v2-{stamp}.csv"
        path.write_text("time_ns,interval_ms,flips,draw_ms\n" + body, encoding="ascii")
        return path

    def test_reject_unrelated_files_and_bounded_to_three(self):
        with tempfile.TemporaryDirectory() as folder:
            names = [f"20261121-12000{i}-000001" for i in range(5)]
            for name in names:
                self.create_csv(folder, name)
            directory = Path(folder) / "profiling"
            (directory / "renderer-v2-20261121-130000-000001.csv").write_text(
                "time_ns,interval_ms,flips,draw_ms\n0,10,2,PRIVATE_PATH\n"
            )
            accepted = report.recent_profile_csvs(folder)
            self.assertEqual([name for name, _ in accepted],
                             [f"renderer-v2-{stamp}.csv" for stamp in names[-3:]])

    def test_reject_large_and_symlink(self):
        with tempfile.TemporaryDirectory() as folder:
            accepted = self.create_csv(folder, "20261121-120000-000001")
            self.create_csv(folder, "20261121-120001-000001", "0,1000,15,1\n" * 150000)
            source = self.create_csv(folder, "20261121-120002-000001")
            link = source.with_name("renderer-v2-20261121-120003-000001.csv")
            try:
                link.symlink_to(source)
            except (OSError, NotImplementedError):
                pass
            self.assertEqual([name for name, _ in report.recent_profile_csvs(folder)],
                             [accepted.name, source.name])

    def test_create_zip_includes_profile(self):
        with tempfile.TemporaryDirectory() as folder:
            path = self.create_csv(folder, "20261121-120000-000001")
            with mock.patch.object(report, "system_text", return_value="System test\n"):
                archive = report.create(folder, {"game_dir": "", "extra_env": ""})
            with zipfile.ZipFile(archive) as z:
                self.assertIn("profiling/" + path.name, z.namelist())
                self.assertEqual(z.read("profiling/" + path.name), path.read_bytes())


if __name__ == "__main__":
    unittest.main()
