"""Geometry and emitted-NC checks for bounded simplification / stay-down links."""
import math
import json
import tempfile
from pathlib import Path
from test_portable_settings import SettingsHarness,FakeVar
import unittest
from shapely.geometry import LineString,Polygon,Point
from shapely import union_all
import cfrp_router_cam as cam
from test_v113_island_pocket import pocket,cfg

class SmoothPathTests(unittest.TestCase):
    def test_dense_circle_reduced_within_tolerance(self):
        pts=[(20*math.cos(i*math.pi/180),20*math.sin(i*math.pi/180)) for i in range(361)]
        pts[-1]=pts[0]
        reduced=cam.simplify_cut_path(pts,.02)
        self.assertLess(len(reduced),len(pts)/2)
        line=LineString(reduced)
        self.assertLessEqual(max(line.distance(Point(p)) for p in pts),.020001)
        self.assertEqual(reduced[0],pts[0]);self.assertEqual(reduced[-1],pts[-1])
        self.assertEqual(cam.simplify_cut_path(pts,0),pts)
    def test_corners_and_tab_transitions_retained(self):
        pts=[(0,0),(1,0),(2,0),(2,1),(2,2)]
        self.assertEqual(cam.simplify_cut_path(pts,.1),[(0,0),(2,0),(2,2)])
        xyz=[(0,0,-2),(1,0,-2),(2,0,-2),(3,0,-1),(4,0,-1),(5,0,-2),(6,0,-2)]
        lines=cam.cut_xyz_lines(xyz,600,.02)
        for expected in ['X2 Y0 Z-2','X3 Y0 Z-1','X4 Y0 Z-1','X5 Y0 Z-2']:
            self.assertTrue(any(expected in line for line in lines))
    def test_invalid_tolerances(self):
        for value in (-1,.11,float('nan'),float('inf')):
            with self.assertRaises(ValueError):cam.path_tolerance({'path_tolerance':value})

class DefaultMigrationTests(unittest.TestCase):
    def test_tolerance_default_migration_preserves_custom_values(self):
        self.assertEqual(cam.path_tolerance({}),.01)
        for version,value,expected in (("1.19",.02,.01),("1.19",0,0),("1.19",.05,.05),("1.20",.02,.02)):
            with self.subTest(version=version,value=value),tempfile.TemporaryDirectory() as tmp:
                path=Path(tmp)/"settings.json"
                path.write_text(json.dumps({'version':version,'vars':{'path_tolerance':value}}))
                app=SettingsHarness(tmp,Path(tmp)/'fallback.json')
                app.vars['path_tolerance']=FakeVar(.01)
                app.load_settings()
                self.assertEqual(app.vars['path_tolerance'].get(),expected)

    def test_old_defaults_off_new_explicit_choices_retained(self):
        for version,expected in (("1.18",False),("1.19",True)):
            with tempfile.TemporaryDirectory() as tmp:
                path=Path(tmp)/"settings.json"
                path.write_text(json.dumps({'version':version,'vars':{'wall_finish':True,'onion_skin_enabled':True}}))
                app=SettingsHarness(tmp,Path(tmp)/'fallback.json')
                app.vars.update(wall_finish=FakeVar(False),onion_skin_enabled=FakeVar(False))
                app.load_settings()
                self.assertEqual(app.vars['wall_finish'].get(),expected)
                self.assertEqual(app.vars['onion_skin_enabled'].get(),expected)

    def test_wear_loss_migrates_from_100m_to_10m_unit(self):
        for saved_vars,expected in (
            ({'tool_wear_loss_per_100m':.79},.079),
            ({'tool_wear_loss_per_100m':0},cam.TOOL_WEAR_DEFAULT_LOSS_PER_10M),
            ({'tool_wear_loss_per_10m':.05},.05),
        ):
            with self.subTest(saved_vars=saved_vars),tempfile.TemporaryDirectory() as tmp:
                path=Path(tmp)/'settings.json'
                path.write_text(json.dumps({'version':'1.20','vars':saved_vars}))
                app=SettingsHarness(tmp,Path(tmp)/'fallback.json')
                app.vars['tool_wear_loss_per_10m']=FakeVar(cam.TOOL_WEAR_DEFAULT_LOSS_PER_10M)
                app.load_settings()
                self.assertAlmostEqual(app.vars['tool_wear_loss_per_10m'].get(),expected)

class PocketLinkTests(unittest.TestCase):
    def test_links_preserve_island_and_reduce_retractions(self):
        for origin in ('Top','Bottom'):
            c=pocket();settings=cfg(z_origin=origin,path_tolerance=.02)
            rough,finish,_=cam.pocket_plan(c,2,settings)
            schedule,level_link=cam.pocket_link_schedule(c,rough,finish,2,settings)
            links=[link for _,_,link in schedule if link]
            self.assertTrue(links)
            free=cam.pocket_free_area(c,2)
            for link in links+([level_link] if level_link else []):
                sweep=LineString(link).buffer(1,quad_segs=32)
                self.assertLessEqual(sweep.difference(free.buffer(.0001)).area,1e-7)
            code=cam.generate_gcode([c],settings)
            old=cam.generate_gcode([c],dict(settings,pocket_stay_down=False))
            self.assertLess(code.count('G0 Z'),old.count('G0 Z'))
            self.assertIn('Pocket stay-down link',code)
            top=settings['stock'] if origin=='Bottom' else 0
            for move in cam.parse_gcode_moves(code):
                if move.rapid and move.start[:2]!=move.end[:2]:
                    self.assertGreaterEqual(move.start[2],top+settings['safe_z']-1e-5)
                if not move.rapid and move.start[:2]!=move.end[:2] and move.end[2]<top:
                    sweep=LineString([move.start[:2],move.end[:2]]).buffer(1,quad_segs=32)
                    self.assertLessEqual(sweep.difference(free.buffer(.0002)).area,1e-5)
    def test_disconnected_pockets_retract(self):
        c=cam.Contour([(0,0),(30,0),(30,10),(0,10)],operation='pocket',role='pocket',
            target_depth=.5,pocket_max_depth=.5,pocket_stock=[(0,0),(30,0),(30,10),(0,10)])
        # Protected strip separates two independently supplied offset rings.
        c.pocket_holes=[[(12,.1),(18,.1),(18,9.9),(12,9.9)]]
        a=[(2,2),(10,2),(10,8),(2,8)]
        b=[(20,2),(28,2),(28,8),(20,8)]
        schedule,level_link=cam.pocket_link_schedule(c,[a,b],[],2,cfg())
        self.assertIsNone(schedule[1][2]);self.assertIsNone(level_link)
    def test_simple_pocket_stays_down_between_depths(self):
        c=pocket();c.pocket_holes=[]
        settings=cfg();rough,finish,_=cam.pocket_plan(c,2,settings)
        schedule,link=cam.pocket_link_schedule(c,rough,finish,2,settings)
        self.assertIsNotNone(link)
        code=cam.generate_gcode([c],settings)
        self.assertIn('G1 Z-0.5',code)
        self.assertEqual(code.count('G0 Z1\n'),1)

if __name__=='__main__':unittest.main()
