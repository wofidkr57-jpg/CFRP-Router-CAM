import importlib.util
import re
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "cfrp_router_cam.py"
SPEC = importlib.util.spec_from_file_location("carbon_cam_v111", SOURCE)
cam = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = cam
SPEC.loader.exec_module(cam)


def square(x0=0.0, y0=0.0, size=100.0, order=None):
    contour = cam.Contour(
        [(x0, y0), (x0 + size, y0), (x0 + size, y0 + size), (x0, y0 + size)],
        closed=True, role="outer", cut_order=order,
    )
    return contour


def config():
    return {
        "safe_z": 5.0, "stock": 2.0, "extra": 0.1, "z_origin": "Top",
        "full_depth": True, "passes": 1, "xy_origin": "좌하단",
        "rapid_optimize": False, "rpm": 18000, "feed": 600.0,
        "plunge": 150.0, "lead": 0.0, "climb": True, "tool_d": 2.0,
        "tool_wear_enabled": True, "tool_wear_loss_per_100m": 100.0,
        "tool_wear_min_d": 0.5,
        "tab_count": 0, "tab_flat": 0.0, "tab_ramp": 0.0,
        "tab_remain": 0.3, "tab_shape": "Flat+ramp", "m8_enabled": False,
        "machine_home_enabled": False, "wall_finish": False,
        "onion_skin_enabled": False, "finish_scope": "전체",
        "onion_skin": 0.2, "finish_allowance": 0.1,
        "finish_feed_pct": 80.0, "auto_trim": False,
        "start_code": cam.DEFAULT_START_CODE, "end_code": cam.DEFAULT_END_CODE,
        "accum_distance_m": 0.0, "accum_time_min": 0.0,
    }


class ArrayOrderAndToolWearTests(unittest.TestCase):
    def test_array_geometry_helpers_preserve_manual_cut_order(self):
        contours = [square(order=1), square(20, 20, 10, order=2)]
        oriented, _, _ = cam.oriented_contour_group(contours, 90)
        normalized, _, _, _ = cam.normalized_contour_group(contours)
        self.assertEqual([c.cut_order for c in oriented], [1, 2])
        self.assertEqual([c.cut_order for c in normalized], [1, 2])

    def test_copied_orders_form_array_wide_cut_stages(self):
        copied = []
        for instance in (1, 2):
            for order in (1, 2):
                contour = square(instance * 200, order * 20, 10, order)
                contour.object_id, contour.instance_id = 1, instance
                copied.append(contour)
        ordered = cam.ordered_contours(copied, rapid_optimize=False)
        self.assertEqual([c.cut_order for c in ordered], [1, 1, 2, 2])

    def test_effective_diameter_uses_accumulated_distance_and_minimum(self):
        cfg = config()
        cfg["tool_wear_loss_per_100m"] = 0.2
        cfg["tool_wear_min_d"] = 1.7
        self.assertAlmostEqual(cam.effective_tool_diameter(cfg, 50.0), 1.9)
        self.assertAlmostEqual(cam.effective_tool_diameter(cfg, 1000.0), 1.7)
        cfg["tool_wear_enabled"] = False
        self.assertAlmostEqual(cam.effective_tool_diameter(cfg, 1000.0), 2.0)

    def test_generated_contours_use_progressively_smaller_diameters(self):
        code = cam.generate_gcode([square(), square(200)], config())
        diameters = [float(value) for value in re.findall(r"\(Contour \d+:.*?tool_d=([0-9.]+)", code)]
        self.assertEqual(len(diameters), 2)
        self.assertGreater(diameters[0], diameters[1])
        self.assertIn("(TOOL_WEAR_COMPENSATION: YES)", code)
        self.assertIn("(TOOL_DIAMETER_JOB_START_MM: 2)", code)
        self.assertIn("(TOOL_DIAMETER_JOB_END_MM:", code)


if __name__ == "__main__":
    unittest.main()
