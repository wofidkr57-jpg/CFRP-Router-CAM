import unittest
import cfrp_router_cam as cam
from test_pocket_compensation import cfg
class InnerTabs(unittest.TestCase):
 def box(self,w=20,h=20): return cam.Contour([(0,0),(w,0),(w,h),(0,h)],role='inner',forced_role='inner',tabs_enabled=False)
 def settings(self,**kw): return cfg(inner_tabs_enabled=True,inner_tab_count=2,tab_count=3,tab_flat=1.,tab_ramp=.35,tool_d=2.,inner_size_adjust=0.,outer_size_adjust=0.,**kw)
 def test_inner_opt_in(self):
  c=self.box();s=self.settings();self.assertEqual(len(cam.safe_auto_tabs(c,[c],s)),2);s['inner_tabs_enabled']=False;self.assertEqual(cam.safe_auto_tabs(c,[c],s),[])
 def test_narrow_slot(self):
  c=self.box(30,4);self.assertEqual(cam.safe_auto_tabs(c,[c],self.settings()),[])
 def test_neighbor_thin_web(self):
  c=self.box(); surround=cam.Contour([(-3,-3),(23,-3),(23,23),(-3,23)])
  self.assertEqual(cam.safe_auto_tabs(c,[c,surround],self.settings()),[])
 def test_nc_inner_tabs_raise_z(self):
  c=self.box();s=self.settings(stock=2.,tab_remain=.3,full_depth=True,lead=0.,tool_change_enabled=False)
  code=cam.generate_gcode([c],s);self.assertIn('tabs=2',code)
  moves=cam.parse_gcode_moves(code);self.assertTrue(any(not m.rapid and abs(m.end[2]+1.7)<1e-5 for m in moves))
 def test_shallow_excluded(self):
  c=self.box();c.target_depth=1.;self.assertEqual(cam.safe_auto_tabs(c,[c],self.settings(stock=6.)),[])
 def test_exact_two_mm_web_excluded(self):
  c=self.box();surround=cam.Contour([(-4,-4),(24,-4),(24,24),(-4,24)])
  self.assertEqual(cam.safe_auto_tabs(c,[c,surround],self.settings()),[])
 def test_rectangle_tabs_span_all_sides(self):
  c=self.box(40,20);s=self.settings();s['inner_tab_count']=4
  tabs=cam.safe_auto_tabs(c,[c],s);self.assertEqual(len(tabs),4)
  gaps=[(tabs[(i+1)%4]-tabs[i])%c.length for i in range(4)]
  self.assertGreaterEqual(min(gaps),20.)
  points=[cam.point_at(c.points,v,True)[0] for v in tabs]
  self.assertTrue(any(y==0 for x,y in points));self.assertTrue(any(y==20 for x,y in points))
 def test_two_tabs_opposite(self):
  c=self.box();tabs=cam.safe_auto_tabs(c,[c],self.settings())
  self.assertAlmostEqual(abs(tabs[1]-tabs[0]),c.length/2)
 def test_manual_tabs_retained(self):
  c=self.box(30,4);c.tabs=[15.];s=self.settings(stock=2.,tab_remain=.3,lead=0.,tool_change_enabled=False)
  self.assertIn('tabs=1',cam.generate_gcode([c],s))
if __name__=='__main__':unittest.main()
