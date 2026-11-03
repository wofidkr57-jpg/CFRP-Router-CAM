import copy,re,unittest
from shapely.geometry import Polygon,LineString
import cfrp_router_cam as cam
from test_pocket_compensation import cfg

def rect(x,y,w,h,name):
 return cam.Contour([(x,y),(x+w,y),(x+w,y+h),(x,y+h)],role='outer',forced_role='outer',object_name=name)
def settings(**kw):
 d=cfg(sheet_w=100.,sheet_h=100.,tool_d=2.,stock=2.,extra=.2,lead=1.,tab_count=0,tool_change_enabled=False,tool_wear_enabled=False,outer_safe_strategy=True,inner_size_adjust=0.,outer_size_adjust=0.);d.update(kw);return d
class OuterSupportTests(unittest.TestCase):
 def test_center_before_edge_overrides_manual(self):
  edge=rect(80,80,12,12,'EDGE');center=rect(42,42,12,12,'CENTER');edge.outer_cut_order=1
  self.assertEqual([c.object_name for c in cam.planned_contours([edge,center],settings())],['CENTER','EDGE'])
 def test_u_cavity_guest_before_host(self):
  host=cam.Contour([(60,20),(90,20),(90,90),(20,90),(20,20),(30,20),(30,80),(80,80),(80,30),(60,30)],role='outer',forced_role='outer',object_name='U')
  guest=rect(40,10,20,60,'GUEST')
  result,relations=cam.support_outer_sequence([host,guest],settings())
  self.assertIs(result[0],guest);self.assertTrue(any(a is guest and b is host for a,b,_ in relations))
 def test_right_side_start_lead_outside_and_exit_same(self):
  c=rect(70,30,20,40,'RIGHT');s=settings();route=cam.compensated_route(c,2,cfg=s)[0]
  r=cam.outer_start_route(c,route,s,[c],2);self.assertGreater(r[0][0],90)
  plan=cam.checked_outer_lead(c,r,s,[c],2);self.assertGreater(plan.entry[0],90)
  code=cam.generate_gcode([c],s);moves=cam.parse_gcode_moves(code)
  cuts=[m for m in moves if not m.rapid and m.start[:2]!=m.end[:2]]
  self.assertAlmostEqual(cuts[0].start[0],cuts[-1].end[0],places=3)
  self.assertAlmostEqual(cuts[0].start[1],cuts[-1].end[1],places=3)
 def test_no_clearance_rejected(self):
  c=rect(30,30,10,10,'C');host=rect(20,20,40,40,'HOST');s=settings();route=cam.compensated_route(c,2,cfg=s)[0]
  with self.assertRaises(ValueError):cam.outer_start_route(c,route,s,[c,host],2)
 def test_support_loss_without_enclosure(self):
  inner=rect(10,10,80,80,'BOUNDARY');inner.role='inner';inner.forced_role='inner'
  c=rect(40,40,10,10,'GUEST')
  risks=cam.support_disconnect_warnings([inner,c],settings())
  self.assertTrue(any(a is c and b is inner for a,b,_ in risks))
 def test_settings_disabled_preserves_legacy(self):
  a=rect(5,5,10,10,'A');b=rect(40,40,10,10,'B');a.outer_cut_order=1
  s=settings(outer_safe_strategy=False)
  self.assertIs(cam.planned_contours([a,b],s)[0],a)
 def test_start_avoids_existing_tab(self):
  c=rect(70,30,20,40,'R');c.tabs=[40.];s=settings(tab_count=1)
  route=cam.compensated_route(c,2,cfg=s)[0];r=cam.outer_start_route(c,route,s,[c],2)
  self.assertGreater(cam.dist(r[0],cam.point_at(c.points,40.,True)[0]),4.)
 def test_both_directions_and_finish_stages(self):
  for climb in (True,False):
   for finish in (False,True):
    c=rect(70,30,20,40,'R');s=settings(climb=climb,wall_finish=finish,onion_skin_enabled=finish)
    code=cam.generate_gcode([c],s)
    self.assertTrue(cam.parse_gcode_moves(code))
 def test_inputs_preserved(self):
  c=rect(70,30,20,40,'R');c.start_s=12;c.tabs=[10.,50.];before=copy.deepcopy(c)
  cam.generate_gcode([c],settings());self.assertEqual(c,before)
if __name__=='__main__':unittest.main()
