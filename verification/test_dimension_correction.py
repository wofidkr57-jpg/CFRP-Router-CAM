import copy
import math
import unittest
import cfrp_router_cam as cam
from test_v105_selection_split import config,square


class DimensionCorrectionTests(unittest.TestCase):
    def cfg(self,**kw):
        c=config();c.update(tool_d=2.,inner_size_adjust=.10,outer_size_adjust=-.14,lead=0,path_tolerance=0)
        c.update(kw);return c

    def test_signed_width_and_zero_legacy(self):
        for role,value in [('inner',.10),('outer',-.14)]:
            c=square(0,0,10,10,role);before=copy.deepcopy(c)
            for sign in (1,-1):
                cfg=self.cfg(**{role+'_size_adjust':sign*value})
                route=cam.compensated_route(c,2,cfg=cfg)[0]
                width=max(x for x,y in route)-min(x for x,y in route)
                actual=width+2 if role=='inner' else width-2
                self.assertAlmostEqual(actual,10+sign*value)
            zero=self.cfg(inner_size_adjust=0,outer_size_adjust=0)
            self.assertEqual(cam.compensated_route(c,2),cam.compensated_route(c,2,cfg=zero))
            self.assertEqual(c,before)

    def test_nc_finish_and_report_match_actual_distance(self):
        for role in ('inner','outer'):
            c=square(0,0,10,10,role);cfg=self.cfg(wall_finish=True,finish_scope='전체',finish_feed_pct=100)
            nc=cam.generate_gcode([c],cfg)
            self.assertIn('(INNER_SIZE_ADJUST_MM: 0.1)',nc)
            self.assertIn('(OUTER_SIZE_ADJUST_MM: -0.14)',nc)
            self.assertIn('tool_d=2',nc)
            finish=nc[nc.index('(Finish contour'):]
            moves=cam.parse_gcode_moves(finish)
            xy=[m.end for m in moves if not m.rapid and m.end[2]<0]
            width=max(p[0] for p in xy)-min(p[0] for p in xy)
            self.assertAlmostEqual(width+(2 if role=='inner' else -2),10+(.1 if role=='inner' else -.14))
            all_moves=cam.parse_gcode_moves(nc)
            distance=sum(math.dist(m.start[:2],m.end[:2]) for m in all_moves if not m.rapid)/1000
            self.assertAlmostEqual(cam.machining_report([c],cfg)[0],distance)

    def test_wear_is_separate_and_open_pockets_excluded(self):
        c=square(0,0,10,10,'inner');cfg=self.cfg(tool_wear_enabled=True,tool_wear_loss_per_10m=.079,tool_wear_min_d=1.9)
        tool=cam.effective_tool_diameter(cfg,5)
        self.assertAlmostEqual(tool,1.9605)
        a=cam.compensated_route(c,tool,cfg=cfg)[0];b=cam.compensated_route(c,tool)[0]
        self.assertAlmostEqual((max(x for x,y in a)-min(x for x,y in a))-(max(x for x,y in b)-min(x for x,y in b)),.1)
        c.closed=False;self.assertEqual(cam.dimension_correction(c,cfg),0)
        c.closed=True;c.operation='pocket';self.assertEqual(cam.dimension_correction(c,cfg),0)

    def test_invalid_and_collision_use_adjusted_route(self):
        a=square(0,0,10,10);b=square(12.05,0,22.05,10)
        self.assertFalse(cam.tool_sweep_collisions([a,b],2,use_parallel=False))
        self.assertTrue(cam.tool_sweep_collisions([a,b],2,use_parallel=False,cfg=self.cfg(outer_size_adjust=.2)))
        for value in (float('nan'),float('inf'),-3):
            with self.assertRaises(ValueError):cam.compensated_route(a,2,cfg=self.cfg(outer_size_adjust=value))


if __name__=='__main__':unittest.main()
