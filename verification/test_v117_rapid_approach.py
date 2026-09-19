"""Check emitted motion order, stock-relative approach and plunge accounting."""
import math
from pathlib import Path
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import cfrp_router_cam as cam
from test_v111_wear_array_order import config, square
from test_v113_island_pocket import pocket

class RapidApproachTests(unittest.TestCase):
    def cfg(self,**kw):
        c=config();c.update(tool_wear_enabled=False,safe_z=10,approach_z=1)
        c.update(kw);return c

    def check_moves(self,contours,cfg):
        code=cam.generate_gcode(contours,cfg)
        top=cfg['stock'] if cfg['z_origin']=='Bottom' else 0
        safe=top+cfg['safe_z'];approach=top+cfg['approach_z']
        moves=cam.parse_gcode_moves(code)
        descents=[]
        for m in moves:
            if m.rapid and m.start[:2]!=m.end[:2]:
                self.assertGreaterEqual(m.start[2],safe-1e-6)
                self.assertGreaterEqual(m.end[2],safe-1e-6)
            if m.rapid and m.end[2]<m.start[2]-1e-6:
                self.assertAlmostEqual(m.end[2],approach)
                self.assertEqual(m.start[:2],m.end[:2])
                descents.append(m)
            if not m.rapid and m.start[:2]==m.end[:2] and m.end[2]<m.start[2]-1e-6:
                self.assertAlmostEqual(m.start[2],approach)
        self.assertTrue(descents)
        lines=code.splitlines()
        for i,line in enumerate(lines):
            if line.startswith('G1 Z'):
                self.assertEqual(lines[i-1],f'G0 Z{cam.fmt(approach)}')
                self.assertIn(f"F{cam.fmt(cfg['plunge'])}",line)
        return code

    def test_top_bottom_multipass_profiles_and_finish(self):
        for origin in ('Top','Bottom'):
            for finish in (False,True):
                cfg=self.cfg(z_origin=origin,full_depth=False,passes=3,
                             wall_finish=finish,lead=1,tab_count=2,tab_flat=1,tab_ramp=1)
                self.check_moves([square(),square(150,0,30)],cfg)

    def test_pocket_every_loop_and_level(self):
        for origin in ('Top','Bottom'):
            cfg=self.cfg(z_origin=origin,stock=3,pocket_stepover=40,pocket_stepdown=.25,pocket_finish=.1)
            self.check_moves([pocket()],cfg)

    def test_open_profile_and_custom_clearance(self):
        c=cam.Contour([(0,0),(20,0)],closed=False)
        self.check_moves([c],self.cfg(approach_z=.5))

    def test_invalid_clearance(self):
        for val in (0,-1,11,float('nan'),float('inf')):
            with self.assertRaises(ValueError):cam.generate_gcode([square()],self.cfg(approach_z=val))

    def test_plunge_time_uses_approach_not_safe_height(self):
        c=square();cfg=self.cfg(full_depth=False,passes=2)
        a=cam.contour_cut_metrics(c,cfg,2,.1,2)
        cfg['safe_z']=30
        b=cam.contour_cut_metrics(c,cfg,2,.1,2)
        self.assertEqual(a,b)
        self.assertAlmostEqual(a[2],((1+1.05)+(1+2.1))/150)

    def test_legacy_settings_default(self):
        cfg=self.cfg();del cfg['approach_z']
        self.assertEqual(cam.rapid_approach_clearance(cfg),1)
        cfg['safe_z']=.5
        self.assertEqual(cam.rapid_approach_clearance(cfg),.5)

if __name__=='__main__':unittest.main()
