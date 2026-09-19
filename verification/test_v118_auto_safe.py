import unittest
import cfrp_router_cam as cam
from test_v111_wear_array_order import config,square

class AutoSafeTests(unittest.TestCase):
    def test_stock_relative_top_bottom(self):
        for stock in (1,2,3,5):
            for origin in ('Top','Bottom'):
                cfg=config();cfg.update(stock=stock,safe_z=99,safe_z_auto=True,approach_z=1,z_origin=origin,tool_wear_enabled=False)
                code=cam.generate_gcode([square()],cfg)
                top=stock if origin=='Bottom' else 0
                moves=cam.parse_gcode_moves(code)
                for m in moves:
                    if m.rapid and m.start[:2]!=m.end[:2]:
                        self.assertAlmostEqual(m.start[2],top+2*stock)
                        self.assertAlmostEqual(m.end[2],top+2*stock)
                self.assertIn(f'G0 Z{cam.fmt(top+1)}',code)
                self.assertEqual(cfg['safe_z'],99)
    def test_manual_setting_retained(self):
        self.assertEqual(cam.resolved_z_config(dict(stock=3,safe_z=10,safe_z_auto=False))['safe_z'],10)
    def test_approach_above_safe_rejected_for_thin_stock(self):
        cfg=config();cfg.update(stock=.3,safe_z_auto=True,approach_z=1)
        with self.assertRaises(ValueError):cam.generate_gcode([square()],cfg)

if __name__=='__main__':unittest.main()
