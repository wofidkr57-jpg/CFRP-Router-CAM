"""Offline checks for opt-in Mach3 G2/G3 profile output."""
import math
import unittest

from shapely.geometry import LineString, Point

import cfrp_router_cam as cam
from test_v105_selection_split import config


class ArcFitTests(unittest.TestCase):
    def test_circle_reduces_blocks_and_tracks_original_chords(self):
        xy=[(10*math.cos(i*math.pi/180),10*math.sin(i*math.pi/180))
            for i in range(0,121,2)]
        xyz=[(x,y,-2.) for x,y in xy]
        lines=cam.cut_xyz_lines(xyz,500,.01,True)
        self.assertLess(len(lines),len(cam.cut_xyz_lines(xyz,500,.01))/4)
        self.assertEqual(len(lines),1)
        self.assertTrue(lines[0].startswith("G3 "))
        arc=cam.fitted_arc(xy,.005)
        self.assertIsNotNone(arc)
        _,ex,ey,ix,jy=arc
        cx,cy=xy[0][0]+ix,xy[0][1]+jy
        radius=math.hypot(xy[0][0]-cx,xy[0][1]-cy)
        self.assertLess(abs(math.hypot(ex-cx,ey-cy)-radius),.001)
        sampled=[(cx+radius*math.cos(i*math.pi/180),cy+radius*math.sin(i*math.pi/180))
                 for i in range(121)]
        original=LineString(xy);emitted=LineString(sampled)
        self.assertLess(max(original.distance(Point(p)) for p in sampled),.005)
        self.assertLess(max(emitted.distance(Point(p)) for p in xy),.005)

    def test_corners_tabs_and_disabled_output(self):
        square=[(0.,0.,-2.),(1.,0.,-2.),(2.,0.,-2.),(2.,1.,-2.),
                (2.,2.,-2.),(1.,2.,-2.),(0.,2.,-2.)]
        lines=cam.cut_xyz_lines(square,500,.01,True)
        self.assertFalse(any(line.startswith(("G2 ","G3 ")) for line in lines))
        xyz=[(0.,0.,-2.),(1.,0.,-2.),(2.,0.,-1.),(3.,0.,-1.),(4.,0.,-2.)]
        lines=cam.cut_xyz_lines(xyz,500,.01,True)
        self.assertTrue(any("X2 Y0 Z-1" in line for line in lines))
        self.assertTrue(any("X4 Y0 Z-2" in line for line in lines))
        self.assertEqual(cam.cut_xyz_lines(xyz,500,.01),
                         cam.cut_xyz_lines(xyz,500,.01,False))
        repeated=[(0.,0.,-2.),(1.,0.,-2.),(1.,0.,-2.),(2.,0.,-2.)]
        self.assertFalse(any(line.startswith(("G2 ","G3 "))
                             for line in cam.cut_xyz_lines(repeated,500,.01,True)))

    def test_complete_program_only_enables_arcs_by_opt_in(self):
        xy=[(12+3*math.cos(2*math.pi*i/120),12+3*math.sin(2*math.pi*i/120))
            for i in range(120)]
        contour=cam.Contour(xy,True,role="inner")
        cfg=config();cfg["path_tolerance"]=.01
        legacy=cam.generate_gcode([contour],cfg)
        self.assertEqual(legacy,cam.generate_gcode([contour],dict(cfg,arc_fit_enabled=False)))
        code=cam.generate_gcode([contour],dict(cfg,arc_fit_enabled=True))
        self.assertIn("(PROFILE_G2_G3: YES)",code)
        self.assertIn("G90 G17 G91.1",code)
        self.assertGreaterEqual(sum(line.startswith(("G2 ","G3 ")) for line in code.splitlines()),2)
        self.assertLess(code.count("G1 X"),legacy.count("G1 X"))
        self.assertTrue(cam.parse_gcode_moves(code))
        self.assertGreater(cam.job_time_estimate(code,0).cutting_minutes,0)


if __name__=="__main__":unittest.main()
