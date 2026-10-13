import math
import re
import unittest
import cfrp_router_cam as cam
from test_v105_selection_split import config

class ContinuousProfileTests(unittest.TestCase):
    def test_closed_profiles_feed_down_without_intermediate_rapid(self):
        for origin in ('Top','Bottom'):
            for arcs in (False,True):
                for role in ('inner','outer'):
                    with self.subTest(origin=origin,arcs=arcs,role=role):
                        pts=[(20+8*math.cos(i*math.pi/60),20+8*math.sin(i*math.pi/60)) for i in range(120)]
                        c=cam.Contour(pts,True,role=role)
                        cfg=dict(config(),stock=6.,extra=.3,full_depth=False,passes=3,lead=1.,z_origin=origin,arc_fit_enabled=arcs,tab_count=3,tab_flat=2.,tab_ramp=.4)
                        code=cam.generate_gcode([c],cfg)
                        self.assertEqual(code.count('(Closed profile: continue next depth'),2)
                        phase=code.split('(Phase:')[1]
                        lines=phase.splitlines()
                        downs=[i for i,l in enumerate(lines) if re.match(r'G1 Z.* F150$',l)]
                        self.assertEqual(len(downs),3)
                        self.assertFalse(any(l.startswith('G0') for l in lines[downs[0]+1:downs[-1]]))
                        moves=cam.parse_gcode_moves(code)
                        target=-6.3 if origin=='Top' else -.3
                        self.assertAlmostEqual(min(m.end[2] for m in moves),target)
                        self.assertEqual(sum(not m.rapid and m.start[:2]==m.end[:2] and m.end[2]<m.start[2]-.01 for m in moves),3)

    def test_open_paths_still_retract_and_single_pass_unchanged(self):
        c=cam.Contour([(0,0),(15,0)],False)
        cfg=dict(config(),full_depth=False,passes=2,stock=6.)
        code=cam.generate_gcode([c],cfg)
        self.assertNotIn('Closed profile: continue',code)
        phase=code.split('(Phase:')[1]
        self.assertGreaterEqual(phase.count('G0 Z'),4)
        circle=cam.Contour([(0,0),(10,0),(10,10),(0,10)],True,role='outer')
        self.assertNotIn('Closed profile: continue',cam.generate_gcode([circle],dict(cfg,passes=1)))

if __name__=='__main__':unittest.main()
