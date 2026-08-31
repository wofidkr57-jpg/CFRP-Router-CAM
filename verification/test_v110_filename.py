import importlib.util
import sys
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "cfrp_router_cam.py"
if not SOURCE.is_file():
    SOURCE = ROOT / "CFRP_Router_CAM_V1.10_source" / "cfrp_router_cam.py"
SPEC = importlib.util.spec_from_file_location("carbon_cam_v110_filename", SOURCE)
cam = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = cam
SPEC.loader.exec_module(cam)


class ThicknessFilenameTests(unittest.TestCase):
    def test_thickness_keeps_one_decimal_and_fractional_precision(self):
        for thickness, expected in [(3, "T3.0"), (1.5, "T1.5"), (3.175, "T3.175")]:
            with self.subTest(thickness=thickness):
                self.assertEqual(cam.stock_thickness_name(thickness), expected)

    def test_thickness_is_after_tool_and_before_source(self):
        name = cam.default_gcode_filename([], "panel.dxf", [], 2, 3, 35,
                                         datetime(2026, 8, 31))
        self.assertEqual(name, "260831_2.0endmill_T3.0_panel_1_35min.nc")
        self.assertEqual(cam.split_gcode_paths(name), (
            "260831_2.0endmill_T3.0_panel_1_35min_PART1.nc",
            "260831_2.0endmill_T3.0_panel_1_35min_PART2.nc",
        ))

    def test_disabled_instances_do_not_increase_quantity(self):
        contours = [cam.Contour([(0, 0), (1, 0), (1, 1)]) for _ in range(3)]
        for i, contour in enumerate(contours, 1):
            contour.object_id, contour.instance_id = 1, i
        contours[-1].enabled = False
        name = cam.default_gcode_filename([], "panel.step", contours, 2, 2.5, 9.4,
                                         datetime(2026, 8, 31))
        self.assertEqual(name, "260831_2.0endmill_T2.5_panel_2_9min.nc")

    def test_save_dialog_and_both_saved_parts_use_stock_thickness(self):
        for split in (False, True):
            with self.subTest(split=split), tempfile.TemporaryDirectory() as folder:
                parts = [("PART1", "G21\nM30\n"), ("PART2", "G21\nM30\n")] if split else []
                app = SimpleNamespace(
                    config=lambda: {"tool_d": 2.0, "stock": 4.5},
                    job_signature=lambda cfg: 123,
                    gcode="G21\nM30\n", gcode_signature=123, gcode_split_mode=split,
                    part_objects=[], filename="panel.dxf", contours=[],
                    gcode_job_minutes=35, gcode_parts=parts, status=mock.Mock(),
                )
                requested = []

                def save_dialog(**kwargs):
                    requested.append(kwargs["initialfile"])
                    return str(Path(folder) / kwargs["initialfile"])

                with mock.patch.object(cam.filedialog, "asksaveasfilename", side_effect=save_dialog), \
                     mock.patch.object(cam.messagebox, "showinfo"):
                    cam.App.save_gcode(app)
                self.assertIn("_2.0endmill_T4.5_panel_1_35min.nc", requested[0])
                paths = sorted(Path(folder).glob("*.nc"))
                self.assertEqual(len(paths), 2 if split else 1)
                for path in paths:
                    self.assertIn("_T4.5_", path.name)
                    self.assertEqual(path.read_text(encoding="ascii"), "G21\nM30\n")
                if split:
                    self.assertTrue(paths[0].name.endswith("_PART1.nc"))
                    self.assertTrue(paths[1].name.endswith("_PART2.nc"))


if __name__ == "__main__":
    unittest.main()
