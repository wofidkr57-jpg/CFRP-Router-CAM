import copy
import unittest
import cfrp_router_cam as cam


class FlipGroupTests(unittest.TestCase):
    def test_reflection_preserves_features_and_other_instances(self):
        part=cam.Contour([(0,0),(12,0),(4,7)],object_id=1,instance_id=1,
                         tabs=[2,8],start_s=3,bridges=[((1,0),(2,0))],
                         pocket_holes=[[(2,1),(3,1),(2,2)]],pocket_stock=[(0,0),(12,0),(4,7)])
        other=copy.deepcopy(part);other.instance_id=2
        before=copy.deepcopy([part,other]);area=part.area
        cam.flip_contour_group([part,other],(1,1))
        self.assertEqual(part.points,[(12,0),(0,0),(8,7)])
        self.assertEqual(part.bridges,[((11,0),(10,0))])
        self.assertEqual(part.pocket_holes,[[(10,1),(9,1),(10,2)]])
        self.assertEqual(part.pocket_stock,part.points)
        self.assertEqual(part.area,-area)
        self.assertEqual(part.tabs,[2,8]);self.assertEqual(part.start_s,3)
        self.assertEqual(other,before[1])
        cam.flip_contour_group([part,other],(1,1))
        self.assertEqual([part,other],before)
