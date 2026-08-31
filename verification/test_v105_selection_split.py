import importlib.util
import sys
import unittest
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "cfrp_router_cam.py"
if not SOURCE.is_file():
    SOURCE = ROOT / "CFRP_Router_CAM_V1.10_source" / "cfrp_router_cam.py"
SPEC = importlib.util.spec_from_file_location("carbon_cam_v110", SOURCE)
cam = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = cam
SPEC.loader.exec_module(cam)


def square(x0, y0, x1, y1, role="outer"):
    return cam.Contour([(x0, y0), (x1, y0), (x1, y1), (x0, y1)],
                       closed=True, role=role)


def config():
    return {
        "safe_z": 5.0, "stock": 2.0, "extra": 0.1, "z_origin": "Top",
        "full_depth": True, "passes": 1, "xy_origin": "좌하단",
        "rapid_optimize": False, "rpm": 18000, "feed": 600.0,
        "plunge": 150.0, "lead": 0.0, "climb": True, "tool_d": 1.0,
        "tab_count": 0, "tab_flat": 0.0, "tab_ramp": 0.0,
        "tab_remain": 0.3, "tab_shape": "Flat+ramp", "m8_enabled": False,
        "machine_home_enabled": False, "wall_finish": False,
        "onion_skin_enabled": False, "finish_scope": "전체",
        "onion_skin": 0.2, "finish_allowance": 0.1,
        "finish_feed_pct": 80.0, "auto_trim": False,
        "start_code": cam.DEFAULT_START_CODE, "end_code": cam.DEFAULT_END_CODE,
        "accum_distance_m": 0.0, "accum_time_min": 0.0,
    }


class SelectionAndSplitTests(unittest.TestCase):
    def test_window_selection_requires_full_containment(self):
        inside = square(2, 2, 8, 8)
        crossing = cam.Contour([(-2, 5), (5, 5)], closed=False)
        rect = (0, 0, 10, 10)
        self.assertTrue(cam.contour_in_selection_rect(inside, rect, crossing=False))
        self.assertFalse(cam.contour_in_selection_rect(crossing, rect, crossing=False))

    def test_crossing_selection_accepts_touching_contour(self):
        crossing = cam.Contour([(-2, 5), (5, 5)], closed=False)
        self.assertTrue(cam.contour_in_selection_rect(crossing, (0, 0, 10, 10), crossing=True))

    def test_split_uses_full_drawing_xy_origin(self):
        left = square(0, 0, 10, 10)
        right = square(100, 0, 110, 10)
        cfg = config()
        common_origin = cam.work_origin_for_contours([left, right], cfg)

        shifted_cfg = dict(cfg)
        shifted_cfg["_xy_origin_override"] = common_origin
        shifted_cfg["_job_label"] = "PART2 OF 2 - REMAINING CONTOURS"
        split_code = cam.generate_gcode([right], shifted_cfg)
        subset_code = cam.generate_gcode([right], cfg)

        split_max_x = max(move.end[0] for move in cam.parse_gcode_moves(split_code))
        subset_max_x = max(move.end[0] for move in cam.parse_gcode_moves(subset_code))
        self.assertGreater(split_max_x, 90.0)
        self.assertLess(subset_max_x, 20.0)
        self.assertIn("Job part: PART2 OF 2 - REMAINING CONTOURS", split_code)

    def test_warns_when_part1_outer_releases_part2_inner(self):
        outer = square(0, 0, 20, 20, role="outer")
        inner = square(5, 5, 10, 10, role="inner")
        self.assertEqual(cam.split_outer_inner_conflicts([outer], [inner]), 1)
        self.assertEqual(cam.split_outer_inner_conflicts([inner], [outer]), 0)

    def test_split_output_names_are_paired(self):
        self.assertEqual(
            cam.split_gcode_paths(r"C:\jobs\panel.nc"),
            (r"C:\jobs\panel_PART1.nc", r"C:\jobs\panel_PART2.nc"),
        )
        self.assertEqual(
            cam.split_gcode_paths(r"C:\jobs\panel_PART1.tap"),
            (r"C:\jobs\panel_PART1.tap", r"C:\jobs\panel_PART2.tap"),
        )

    def test_default_filename_uses_requested_format(self):
        source = r"C:\parts\ARM FRAME.step"
        parts = [cam.PartObject(1, "ARM FRAME", [], source_path=source)]
        contours = [square(0, 0, 10, 10) for _ in range(3)]
        for instance, contour in enumerate(contours, 1):
            contour.object_id = 1
            contour.instance_id = instance
        name = cam.default_gcode_filename(
            parts, source, contours, 2.0, 3.0, 34.6, datetime(2026, 8, 30)
        )
        self.assertEqual(name, "260830_2.0endmill_T3.0_ARM_FRAME_3_35min.nc")

    def test_multiple_source_files_use_multi(self):
        parts = [
            cam.PartObject(1, "A", [], source_path=r"C:\parts\A.dxf"),
            cam.PartObject(2, "B", [], source_path=r"C:\parts\B.step"),
        ]
        contours = [square(0, 0, 10, 10), square(20, 0, 30, 10)]
        for object_id, contour in enumerate(contours, 1):
            contour.object_id = object_id
            contour.instance_id = 1
        name = cam.default_gcode_filename(
            parts, "multi_job", contours, 3.175, 1.5, 9.6, datetime(2026, 8, 30)
        )
        self.assertEqual(name, "260830_3.175endmill_T1.5_multi_2_10min.nc")

    def test_one_step_split_into_parts_keeps_source_filename(self):
        source = r"C:\parts\CARBON PIN.step"
        parts = [
            cam.PartObject(1, "CARBON PIN_P1", [], source_path=source),
            cam.PartObject(2, "CARBON PIN_P2", [], source_path=source),
        ]
        self.assertEqual(cam.loaded_source_name(parts, "multi_job"), "CARBON_PIN")


if __name__ == "__main__":
    unittest.main()
