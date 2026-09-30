"""Optional bore-first phases must agree across ordering and generated NC."""
import copy
import re
import unittest

import cfrp_router_cam as cam
from test_pocket_compensation import counterbore, cfg


def sample():
    pocket = counterbore()
    pocket.layer = "BORE"
    shallow = cam.Contour([(30, 0), (42, 0), (42, 12), (30, 12)], role="inner",
                          layer="SHALLOW", target_depth=.8, cut_order=9)
    deep = cam.Contour([(50, 0), (62, 0), (62, 12), (50, 12)], role="inner",
                       layer="DEEP", target_depth=1.6, cut_order=8)
    through = cam.Contour([(70, 0), (82, 0), (82, 12), (70, 12)], role="inner",
                          layer="THROUGH", cut_order=2)
    outer = cam.Contour([(90, 0), (110, 0), (110, 20), (90, 20)], role="outer",
                        layer="OUTER", cut_order=1)
    return [outer, through, deep, pocket, shallow]


def sample_with_shallow_outer():
    contours = sample()
    contours.append(cam.Contour([(115, 0), (125, 0), (125, 10), (115, 10)],
                                role="outer", layer="OUTER_1T", target_depth=1.,
                                outer_cut_order=9))
    contours.append(cam.Contour([(130, 0), (140, 0), (140, 10), (130, 10)],
                                role="outer", layer="OUTER_FULL", target_depth=6.,
                                outer_cut_order=1))
    return contours


class DepthFirstOrderTests(unittest.TestCase):
    def test_opt_in_phases_override_manual_rank_but_keep_geometry(self):
        contours = sample()
        before = copy.deepcopy(contours)
        expected = ["BORE", "SHALLOW", "DEEP", "THROUGH", "OUTER"]
        for rapid in (False, True):
            for mode in ("nearest", "center_cw", "center_ccw"):
                ordered = cam.ordered_contours(contours, rapid, outer_order=mode,
                                                sheet_center=(60, 30) if mode != "nearest" else None,
                                                depth_first=True)
                self.assertEqual([c.layer for c in ordered], expected)
        self.assertEqual(contours, before)
        self.assertNotEqual([c.layer for c in cam.ordered_contours(contours, False)], expected)

    def test_no_bore_keeps_existing_order_even_when_selected(self):
        contours = [c for c in sample() if c.layer in ("THROUGH", "OUTER")]
        self.assertEqual(cam.ordered_contours(contours, False, depth_first=True),
                         cam.ordered_contours(contours, False))

    def test_shallow_outer_is_depth_first_but_stock_depth_outer_stays_last(self):
        contours = sample_with_shallow_outer()
        before = copy.deepcopy(contours)
        expected = ["BORE", "SHALLOW", "OUTER_1T", "DEEP", "THROUGH", "OUTER_FULL", "OUTER"]
        for rapid in (False, True):
            for mode in ("nearest", "center_cw", "center_ccw"):
                ordered = cam.ordered_contours(contours, rapid, outer_order=mode,
                                               sheet_center=(70, 30) if mode != "nearest" else None,
                                               depth_first=True, stock_thickness=6.)
                self.assertEqual([c.layer for c in ordered], expected)
        self.assertEqual(contours, before)
        # An external 1T profile by itself must activate depth-first ordering.
        no_bore = [c for c in contours if c.layer in ("OUTER_1T", "THROUGH", "OUTER_FULL")]
        self.assertEqual([c.layer for c in cam.ordered_contours(no_bore, False, depth_first=True,
                                                                stock_thickness=6.)],
                         ["OUTER_1T", "THROUGH", "OUTER_FULL"])
        self.assertEqual([c.layer for c in cam.ordered_contours(no_bore, False, depth_first=True,
                                                                stock_thickness=1.)],
                         ["THROUGH", "OUTER_FULL", "OUTER_1T"])

    def test_shallow_outer_is_first_in_nc_without_releasing_full_depth_outer(self):
        settings = cfg(stock=6., extra=.2, sheet_w=150., sheet_h=50., lead=0.,
                       rapid_optimize=False, tab_count=0, tool_change_enabled=False,
                       depth_first_order=True)
        code = cam.generate_gcode(sample_with_shallow_outer(), dict(settings))
        labels = re.findall(r"\(Contour \d+: .*?layer=([^,]+)", code)
        self.assertEqual(labels, ["SHALLOW", "OUTER_1T", "DEEP", "THROUGH", "OUTER_FULL", "OUTER"])
        self.assertLess(code.index("(ISLAND POCKET 1:"), code.index("(Contour 2:"))
        self.assertIn("(DEPTH_FIRST_ORDER: YES)", code)
        self.assertTrue(cam.parse_gcode_moves(code))

    def test_nc_order_and_default_remain_separate(self):
        contours = sample()
        settings = cfg(stock=6., extra=.2, sheet_w=140., sheet_h=50., lead=0.,
                       rapid_optimize=False, tab_count=0, tool_change_enabled=False,
                       depth_first_order=True)
        code = cam.generate_gcode(contours, dict(settings))
        labels = re.findall(r"\(Contour \d+: .*?layer=([^,]+)", code)
        self.assertEqual(labels, ["SHALLOW", "DEEP", "THROUGH", "OUTER"])
        self.assertLess(code.index("(ISLAND POCKET 1:"), code.index("(Contour 2:"))
        self.assertIn("(DEPTH_FIRST_ORDER: YES)", code)
        self.assertTrue(cam.parse_gcode_moves(code))
        settings["depth_first_order"] = False
        old_code = cam.generate_gcode(contours, dict(settings))
        self.assertNotEqual(re.findall(r"\(Contour \d+: .*?layer=([^,]+)", old_code), labels)
        self.assertIn("(DEPTH_FIRST_ORDER: NO)", old_code)
        settings.pop("depth_first_order")
        self.assertEqual(old_code, cam.generate_gcode(contours, dict(settings)))


if __name__ == "__main__":
    unittest.main()
