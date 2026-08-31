import importlib.util
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "cfrp_router_cam.py"
if not SOURCE.is_file():
    SOURCE = ROOT / "CFRP_Router_CAM_V1.10_source" / "cfrp_router_cam.py"
SPEC = importlib.util.spec_from_file_location("carbon_cam_v110_language", SOURCE)
cam = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = cam
SPEC.loader.exec_module(cam)


def square():
    contour = cam.Contour([(0, 0), (20, 0), (20, 10), (0, 10)], closed=True,
                          role="outer", layer="한글 레이어")
    contour.object_name = "한글 부품"
    return contour


def config():
    return {
        "show_grid": True,
        "tool_d": 2.0, "rpm": 22000.0, "feed": 800.0, "plunge": 200.0,
        "stock": 3.0, "extra": 0.1, "safe_z": 10.0, "lead": 1.0,
        "passes": 2, "tab_count": 3, "tab_flat": 1.0, "tab_remain": 0.2,
        "tab_ramp": 0.35, "z_origin": "Bottom", "xy_origin": "좌하단",
        "climb": True, "full_depth": False, "rapid_optimize": True,
        "m8_enabled": True, "machine_home_enabled": True,
        "machine_park_x": 10.0, "machine_park_y": 10.0, "machine_park_z": -2.0,
        "wall_finish": False, "onion_skin_enabled": False, "finish_scope": "전체",
        "onion_skin": 0.2, "finish_allowance": 0.12, "finish_feed_pct": 80.0,
        "tab_shape": "Flat+ramp", "accum_distance_m": 5.0, "accum_time_min": 30.0,
        "gap_tol": 0.2, "sheet_w": 250.0, "sheet_h": 500.0,
        "array_gap": 5.0, "array_edge": 3.0, "array_qty": 4,
        "array_rotate": True, "array_auto_rotate": True, "auto_trim": False,
        "start_code": cam.DEFAULT_START_CODE, "end_code": cam.DEFAULT_END_CODE,
    }


class LanguageAndNcHeaderTests(unittest.TestCase):
    def test_english_ui_core_and_dynamic_text_contains_no_hangul(self):
        previous = cam.CURRENT_LANGUAGE
        try:
            cam.CURRENT_LANGUAGE = "en"
            self.assertEqual(cam.ui_text("DXF 열기"), "Open DXF")
            dynamic = cam.ui_text("선택 윤곽 3개 안전검사 제외")
            self.assertFalse(any("가" <= char <= "힣" for char in dynamic))
            self.assertIn("Contour", dynamic)
        finally:
            cam.CURRENT_LANGUAGE = previous

    def test_saved_language_is_read_from_settings(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "settings.json"
            path.write_text(json.dumps({"language": "en"}), encoding="utf-8")
            with mock.patch.object(cam, "startup_settings_candidates", return_value=[str(path)]):
                with mock.patch.dict(os.environ, {}, clear=False):
                    os.environ.pop("CFRP_CAM_LANGUAGE", None)
                    self.assertEqual(cam.saved_interface_language(), "en")

    def test_nc_header_records_conditions_and_is_ascii_only(self):
        code = cam.generate_gcode([square()], config())
        self.assertTrue(code.startswith("%\nO0001\n("))
        self.assertIn("(----- CAM SETTINGS BEGIN -----)", code)
        self.assertIn("(TOOL_DIAMETER_MM: 2)", code)
        self.assertIn("(SPINDLE_RPM: 22000)", code)
        self.assertIn("(STOCK_THICKNESS_MM: 3)", code)
        self.assertIn("(THROUGH_ALLOWANCE_MM: 0.1)", code)
        self.assertIn("(DEFAULT_FINAL_Z: -0.1)", code)
        self.assertIn("(Z_ORIGIN: BOTTOM)", code)
        self.assertIn("(XY_ORIGIN_MODE: LOWER_LEFT)", code)
        self.assertIn("(PROGRAMMED_PASS_COUNT: 2)", code)
        self.assertIn("(COOLANT_AIR_M8: YES)", code)
        self.assertIn("(MACHINE_HOME_G53_PARK: YES)", code)
        self.assertIn("(ARRAY_REQUESTED_QTY: 4)", code)
        self.assertIn("G21", code)
        self.assertNotIn("한글", code)
        self.assertTrue(all(ord(char) < 128 for char in code))

    def test_english_origin_enum_keeps_geometry_behavior(self):
        contour = square()
        cfg = config()
        cfg["xy_origin"] = "Lower-left"
        self.assertEqual(cam.work_origin_for_contours([contour], cfg), (0, 0))


if __name__ == "__main__":
    unittest.main()
