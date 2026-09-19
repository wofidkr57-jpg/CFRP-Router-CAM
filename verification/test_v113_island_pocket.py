import copy
import math
from pathlib import Path
import re
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import cfrp_router_cam as cam
import test_v112_projection_preflight as v112
from test_v111_wear_array_order import config
from shapely.geometry import Polygon,LineString
from shapely import union_all


def pocket(open_side=False):
    outer=[(0,0),(40,0),(40,30),(0,30)]
    island=[(15,10),(40 if open_side else 25,10),(40 if open_side else 25,20),(15,20)]
    region=Polygon(outer).difference(Polygon(island))
    return cam.Contour(list(region.exterior.coords)[:-1],operation='pocket',role='pocket',
                       target_depth=.5,pocket_max_depth=.5,pocket_stock=outer,
                       pocket_holes=[list(r.coords)[:-1] for r in region.interiors],tabs_enabled=False)

def cfg(**kwargs):
    c=config();c.update(tool_wear_enabled=False,tool_d=2,stock=3,pocket_stepover=40,
                       pocket_stepdown=.25,pocket_finish=.1);c.update(kwargs);return c

class IslandPocketTests(unittest.TestCase):
    def test_closed_and_open_island_sweeps_are_protected(self):
        for opened in (False,True):
            c=pocket(opened);rough,finish,residual=cam.pocket_plan(c,2,cfg())
            sweep=union_all([LineString(p+[p[0]]).buffer(1,quad_segs=32) for p in rough+finish])
            material=Polygon(c.pocket_stock).difference(Polygon(c.points,c.pocket_holes))
            self.assertLess(sweep.intersection(material).area,1e-5)
            self.assertLess(residual,3) # sharp reentrant corners remain tool-radius limited
            self.assertGreater(len(rough),1);self.assertGreater(len(finish),0)
    def test_stepover_limits_and_depth_guard(self):
        for key,value in [('pocket_stepover',0),('pocket_stepover',51),('pocket_stepdown',0),
                          ('pocket_finish',-1),('pocket_stepdown',float('nan'))]:
            with self.assertRaises(ValueError):cam.pocket_plan(pocket(),2,cfg(**{key:value}))
        for depth in (None,.6,float('inf')):
            c=pocket();c.target_depth=depth
            with self.assertRaises(ValueError):cam.pocket_plan(c,2,cfg())
        with self.assertRaises(ValueError):cam.pocket_plan(pocket(),2,cfg(tool_wear_enabled=True))
    def test_small_closed_pocket_rejects_oversize_tool(self):
        c=pocket();c.points=[(18,14),(19,14),(19,15),(18,15)];c.pocket_holes=[]
        with self.assertRaises(ValueError):cam.pocket_plan(c,2,cfg())
    def test_offsets_order_depth_and_retract_connections(self):
        c=pocket();outer=cam.Contour(c.pocket_stock,role='outer',cut_order=1,tabs_enabled=False)
        code=cam.generate_gcode([outer,c],cfg())
        self.assertLess(code.index('ISLAND POCKET'),code.index('(Contour 2: outer'))
        section=code.split('(ISLAND POCKET')[1].split('(Contour 2:')[0]
        plunges=[float(v) for v in re.findall(r'^G1 Z(-?[0-9.]+)',section,re.M)]
        self.assertEqual(set(plunges),{-.25,-.5})
        for movement in cam.parse_gcode_moves(section):
            if movement.rapid and movement.start[:2]!=movement.end[:2]:
                self.assertGreaterEqual(movement.start[2],5)
                self.assertGreaterEqual(movement.end[2],5)
        self.assertEqual(section.count('G0 Z5'),2*len(plunges))
    def test_bottom_and_xy_origin(self):
        c=pocket();code=cam.generate_gcode([c],cfg(z_origin='Bottom',_xy_origin_override=(7,9)))
        self.assertIn('G1 Z2.75',code);self.assertIn('G1 Z2.5',code);self.assertIn('G0 Z8',code)
        top=cam.generate_gcode([c],cfg(_xy_origin_override=(0,0)))
        getxy=lambda s:next(m.end[:2] for m in cam.parse_gcode_moves(s) if m.start[:2]!=m.end[:2])
        a,b=getxy(top),getxy(code)
        self.assertAlmostEqual(a[0]-b[0],7,places=3);self.assertAlmostEqual(a[1]-b[1],9,places=3)
    def test_transform_and_array_keep_islands_attached(self):
        c=pocket();before=Polygon(c.points,c.pocket_holes).area
        group,_,_=cam.oriented_contour_group([c],37)
        cam.move_contour_group(group,(0,1),100,50)
        cam.rotate_contour_group(group,(0,1),90)
        moved=group[0]
        self.assertAlmostEqual(Polygon(moved.points,moved.pocket_holes).area,before)
        self.assertGreater(min(x for x,y in moved.pocket_stock),70)
        cam.pocket_plan(moved,2,cfg())
    def test_adjacent_part_blocks_open_edge_sweep(self):
        c=pocket();other=cam.Contour([(40.1,0),(50,0),(50,30),(40.1,30)],role='outer')
        self.assertTrue(cam.pocket_job_issues([c,other],cfg()))
        with self.assertRaises(ValueError):cam.generate_gcode([c,other],cfg())
        other.points=[(x+10,y) for x,y in other.points]
        self.assertFalse(cam.pocket_job_issues([c,other],cfg()))
    def test_metrics_include_all_pocket_paths(self):
        c=pocket();r,f,_=cam.pocket_plan(c,2,cfg())
        mm,mins,plunge=cam.contour_cut_metrics(c,cfg(),3,.1,2)
        self.assertAlmostEqual(mm,sum(cam.path_length(p,True) for p in r+f)*2)
        self.assertGreater(plunge,0);self.assertGreater(mins,0)
    def test_pocket_does_not_change_profile_classification(self):
        c=pocket();outer=cam.Contour(c.pocket_stock)
        hole=cam.Contour([(5,5),(7,5),(7,7),(5,7)])
        cam.classify_contours([c,outer,hole]);self.assertEqual([c.role,outer.role,hole.role],['pocket','outer','inner'])
    def test_split_detects_outer_before_open_edge_pocket(self):
        c=pocket(True);outer=cam.Contour(c.pocket_stock,role='outer')
        self.assertEqual(cam.split_outer_inner_conflicts([outer],[c]),1)
    def test_disabled_pocket_is_not_generated(self):
        c=pocket();c.enabled=False
        code=cam.generate_gcode([cam.Contour(c.pocket_stock),c],cfg())
        self.assertNotIn('(ISLAND POCKET ',code)

class StepPocketImportTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):v112.ProjectionTests.setUpClass()
    @classmethod
    def tearDownClass(cls):v112.ProjectionTests.tearDownClass()
    def test_real_brep_floor_depths_and_opt_out(self):
        fixture=v112.ProjectionTests
        cs,stock,_,_=cam.step_faces_to_2d_features(fixture.model,fixture.tops,cam.mat_identity(),include_pockets=True)
        pockets=[c for c in cs if c.operation=='pocket']
        self.assertEqual(sorted(round(c.target_depth,3) for c in pockets),[.6,1.0])
        for c in pockets:cam.pocket_plan(c,1,cfg(tool_d=1))
        profiles,_,_,_=cam.step_faces_to_2d_features(fixture.model,fixture.tops,cam.mat_identity())
        self.assertFalse(any(c.operation=='pocket' for c in profiles))
        sequence=cam.ordered_contours(cs)
        self.assertEqual(sequence[:len(pockets)],sorted(pockets,key=lambda c:c.target_depth))

if __name__=='__main__':unittest.main()
