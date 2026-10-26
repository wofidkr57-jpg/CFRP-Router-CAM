"""Offline bounds versus generated cuts, including leads and finishing."""
import math
from pathlib import Path
import sys
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import cfrp_router_cam as cam
from test_touch_geometry import cfg, outer


class TouchBoundaryTests(unittest.TestCase):
    def test_encloses_generated_tool_sweep_with_lead_finish_wear(self):
        for angle in (0,27,90):
            for finish in (False,True):
                with self.subTest(angle=angle,finish=finish):
                    contour=outer(object_id=1,instance_id=1)
                    cam.rotate_contour_group([contour],(1,1),angle)
                    settings=cfg(lead=3.,wall_finish=finish,finish_allowance=2.,
                                 tool_wear_enabled=True,preflight_z=30.,preflight_feed=1000.,
                                 start_code="G21 G90 G17 G54\nG0 X0 Y0 Z10",end_code="M5\nM30")
                    code,bounds=cam.touch_boundary_program([contour],settings)
                    cut=cam.generate_gcode([contour],settings)
                    moves=[m for m in cam.parse_gcode_moves(cut) if not m.rapid and min(m.start[2],m.end[2])<0]
                    self.assertTrue(moves)
                    x0,y0,x1,y1=bounds
                    for move in moves:
                        for x,y,_ in (move.start,move.end):
                            self.assertGreaterEqual(x-1.,x0-.01)
                            self.assertLessEqual(x+1.,x1+.01)
                            self.assertGreaterEqual(y-1.,y0-.01)
                            self.assertLessEqual(y+1.,y1+.01)
                    self.assertNotIn("M880",code)
                    self.assertNotIn("M881",code)
                    self.assertIn("M5",code)

    def test_z_clearance_and_current_origin(self):
        for datum,height in (("Top",30.),("Bottom",33.)):
            settings=cfg(z_origin=datum,preflight_z=30.,preflight_feed=900.,
                         touch_xy_mode="current",touch_origin_x=50.,touch_origin_y=70.)
            code,_=cam.touch_boundary_program([outer()],settings)
            self.assertIn(f"G0 Z{cam.fmt(height)}",code)
            self.assertIn("G10 L2 P1 X50 Y70",code)
            moves=cam.parse_gcode_moves(code)
            self.assertTrue(all(m.start[2]>=height for m in moves if m.start[:2]!=m.end[:2]))

    def test_invalid_empty_and_clearance(self):
        with self.assertRaises(ValueError):cam.touch_boundary_program([],cfg())
        for value in (0.,-1.,math.nan,math.inf,1.):
            with self.subTest(value=value),self.assertRaises(ValueError):
                cam.touch_boundary_program([outer()],cfg(preflight_z=value,safe_z=5.))


if __name__=="__main__":unittest.main()
