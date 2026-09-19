"""Public synthetic fixtures for transformed STEP projection seams."""
import sys
from pathlib import Path
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import cfrp_router_cam as cam
from shapely.geometry import box
from shapely.affinity import rotate, translate

class SeamTests(unittest.TestCase):
    def test_numerical_gap_preserves_hole_and_area(self):
        left=box(0,0,10,20).difference(box(2,5,5,8))
        right=box(10+1e-9,0,20,20)
        for angle in (0,37,90):
            shapes=[translate(rotate(p,angle,origin=(0,0)),123.456,-99.321) for p in (left,right)]
            result=cam.connected_step_projection(shapes)
            self.assertTrue(result.is_valid)
            self.assertEqual(len(result.interiors),1)
            self.assertAlmostEqual(result.area,391,places=5)
    def test_planar_mesh_seam_is_not_an_opening(self):
        points=[(0,0,0),(20,0,0),(20,20,0),
                (0,1e-10,0),(20-1e-10,20,0),(0,20,0)]
        face=cam.StepFace(points,[(0,1,2),(3,4,5)],(0,0,1),(10,10,0))
        model=cam.StepModel("synthetic",[face],points,
                            face_components=[0],component_vertices={0:points})
        for angle in (0,37,90):
            matrix=cam.mat_mul(cam.mat_translate(123.456,-99.321,0),cam.mat_rotate_z(angle))
            loops=cam.step_component_projection(model,0,matrix)
            self.assertEqual(len(loops),1)
            self.assertEqual(len(loops[0]),4)
            self.assertAlmostEqual(abs(cam.signed_area(loops[0])),400,places=6)

    def test_real_gap_is_not_bridged_or_discarded(self):
        for gap in (.001,1,10):
            with self.assertRaises(ValueError):
                cam.connected_step_projection([box(0,0,10,10),box(10+gap,0,20+gap,10)])
    def test_valid_polygon_unchanged(self):
        p=box(0,0,20,20).difference(box(5,5,10,10))
        self.assertTrue(cam.connected_step_projection([p]).equals_exact(p,0))

if __name__=='__main__':unittest.main()
