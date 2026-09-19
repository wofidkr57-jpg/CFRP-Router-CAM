"""Synthetic public fixtures only; customer STEP files must not be committed."""
import math
import os
from pathlib import Path
import sys
import tempfile
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import cfrp_router_cam as cam
from test_v111_wear_array_order import config, square

class ProjectionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from OCP.BRepPrimAPI import BRepPrimAPI_MakeBox,BRepPrimAPI_MakeCylinder
        from OCP.BRepAlgoAPI import BRepAlgoAPI_Fuse,BRepAlgoAPI_Cut
        from OCP.gp import gp_Pnt,gp_Ax2,gp_Dir
        from OCP.STEPControl import STEPControl_Writer,STEPControl_AsIs
        base=BRepPrimAPI_MakeBox(gp_Pnt(0,0,0),40,30,2).Shape()
        boss=BRepPrimAPI_MakeBox(gp_Pnt(10,5,2),30,20,1).Shape()
        body=BRepAlgoAPI_Fuse(base,boss).Shape()
        # Through hole in the raised area, separate hole in the lower floor,
        # and a blind counterbore around the first through hole.
        for x,y,z,r,h in [(25,15,-1,2,5),(5,15,-1,1,5),(25,15,2.4,3,2)]:
            tool=BRepPrimAPI_MakeCylinder(gp_Ax2(gp_Pnt(x,y,z),gp_Dir(0,0,1)),r,h).Shape()
            body=BRepAlgoAPI_Cut(body,tool).Shape()
        cls.temp=tempfile.TemporaryDirectory()
        path=os.path.join(cls.temp.name,'synthetic.step')
        writer=STEPControl_Writer();writer.Transfer(body,STEPControl_AsIs);writer.Write(path)
        cls.model=cam.load_step_model(path)
        cls.tops=[i for i,f in enumerate(cls.model.faces) if f.normal[2]>.999 and abs(f.center[2]-3)<.001]
        cls.lower=[i for i,f in enumerate(cls.model.faces) if f.normal[2]>.999 and abs(f.center[2]-2)<.001]
    @classmethod
    def tearDownClass(cls):cls.temp.cleanup()
    def convert(self,indices,matrix=None):
        return cam.step_faces_to_2d_features(self.model,indices,matrix or cam.mat_identity())
    def test_boss_and_floor_select_same_body_and_holes(self):
        for selected in (self.tops,self.lower,self.tops+self.lower):
            contours,stock,_,_=self.convert(selected)
            self.assertEqual(len([c for c in contours if c.role=='outer']),1)
            self.assertAlmostEqual(abs(contours[0].area),1200,places=5)
            self.assertAlmostEqual(stock,3)
            self.assertEqual(len(contours),4)
            self.assertEqual(len([c for c in contours if c.target_depth is not None]),1)
            self.assertAlmostEqual(next(c.target_depth for c in contours if c.target_depth is not None),.6)
    def test_rotated_translated_body(self):
        m=cam.mat_mul(cam.mat_translate(70,-20,8),cam.mat_rotate_z(37))
        contours,stock,_,_=self.convert(self.tops,m)
        self.assertAlmostEqual(abs(contours[0].area),1200,places=5)
        self.assertAlmostEqual(stock,3)
    def test_other_component_not_imported(self):
        import copy
        m=cam.StepModel("synthetic",list(self.model.faces),list(self.model.vertices))
        # Mesh-only translated second body, retaining disjoint connectivity.
        from dataclasses import replace
        extra=[replace(f,vertices=[(x+100,y,z) for x,y,z in f.vertices],center=(f.center[0]+100,*f.center[1:]),topo_shape=None) for f in self.model.faces]
        m.faces.extend(extra);m.vertices.extend([(x+100,y,z) for x,y,z in self.model.vertices])
        m.face_components=[];m.component_vertices={}
        contours,_,_,_=cam.step_faces_to_2d_features(m,self.tops,cam.mat_identity())
        self.assertTrue(all(x<=40.001 for c in contours for x,y in c.points))

class PreflightTests(unittest.TestCase):
    def cfg(self,**values):
        cfg=config();cfg.update(preflight_enabled=True,preflight_z=30,preflight_feed=900);cfg.update(values);return cfg
    def test_disabled_preserves_existing_output(self):
        self.assertNotIn('PREFLIGHT BEGIN',cam.generate_gcode([square()],config()))
    def test_once_before_cutting_and_closed(self):
        code=cam.generate_gcode([square()],self.cfg())
        self.assertEqual(code.count('PREFLIGHT BEGIN'),1)
        self.assertLess(code.index('PREFLIGHT END'),code.index('(Contour 1:'))
        preview=code.split('(PREFLIGHT BEGIN')[1].split('(PREFLIGHT END)')[0]
        self.assertIn('G0 Z30',preview)
        self.assertNotIn('G1 Z',preview)
        self.assertEqual(preview.count('G1 X0 Y0 F900'),3) # start, close, return
    def test_bottom_origin_adds_stock(self):
        lines=cam.preflight_gcode([square()],self.cfg(z_origin='Bottom'),(0,0))
        self.assertIn('G0 Z32',lines)
        self.assertIn('G0 Z7',lines)
    def test_origin_and_disabled_contours(self):
        a=square(20,40,10);b=square(500,500,10);b.enabled=False
        lines=cam.preflight_gcode([a,b],self.cfg(),(20,40))
        self.assertIn('G1 X10 Y10 F900',lines)
        self.assertFalse(any('500' in line for line in lines))
    def test_holes_only_job_uses_bounds(self):
        a=square(20,40,10);a.role='inner'
        self.assertIn('G1 X10 Y10 F900',cam.preflight_gcode([a],self.cfg(),(20,40)))
    def test_invalid_clearance_feed_rejected(self):
        for v in (0,4,float('nan'),float('inf')):
            with self.assertRaises(ValueError):cam.generate_gcode([square()],self.cfg(preflight_z=v))
        for v in (0,-1,float('nan'),float('inf')):
            with self.assertRaises(ValueError):cam.generate_gcode([square()],self.cfg(preflight_feed=v))

if __name__=='__main__':unittest.main()
