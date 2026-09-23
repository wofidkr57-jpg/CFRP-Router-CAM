import copy
import sys
import unittest
from pathlib import Path
from shapely.affinity import rotate, translate
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import cfrp_router_cam as cam


def part(oid,points,qty=1,offset=None):
    return cam.PartObject(oid,f'part {oid}',[cam.Contour(points,True,role='outer')],quantity=qty,nest_offset=offset)


def placed_shape(source,placement):
    shape=rotate(cam.nesting_outline(source),placement.angle,origin=(0,0))
    x,y,_,_=shape.bounds
    return translate(shape,placement.x-x,placement.y-y)


class ContourNestingTests(unittest.TestCase):
    def assert_clear(self,parts,placements,width,height,gap,edge):
        by_id={p.object_id:p for p in parts};shapes=[]
        for p in placements:
            source=by_id[p.object_id];shape=placed_shape(source,p);offset=cam.nesting_offset(source,gap)
            x0,y0,x1,y1=shape.bounds
            self.assertGreaterEqual(x0,edge+offset-1e-6);self.assertGreaterEqual(y0,edge+offset-1e-6)
            self.assertLessEqual(x1,width-edge-offset+1e-6);self.assertLessEqual(y1,height-edge-offset+1e-6)
            for other,other_offset in shapes:
                self.assertLess(shape.intersection(other).area,1e-7)
                self.assertGreaterEqual(shape.distance(other),offset+other_offset-1e-6)
            shapes.append((shape,offset))

    def test_interlocking_beats_boxes_and_preserves_source(self):
        p=part(1,[(0,0),(40,0),(0,20)],2,.5);before=copy.deepcopy(p)
        placements,counts=cam.best_contour_nesting([p],45,30,1,0,(0,180))
        box,_=cam.best_mixed_nesting([p],45,30,1,0,(0,180))
        self.assertEqual(counts,{1:2});self.assertEqual(len(box),1)
        self.assertEqual({q.angle for q in placements},{0,180})
        self.assert_clear([p],placements,45,30,1,0);self.assertEqual(p,before)

    def test_individual_offsets_sum_and_quantity(self):
        parts=[part(1,[(0,0),(10,0),(10,10),(0,10)],2,1),part(2,[(0,0),(8,0),(8,8),(0,8)],2,2)]
        placements,counts=cam.best_contour_nesting(parts,60,35,99,3,(0,180))
        self.assertEqual(counts,{1:2,2:2});self.assert_clear(parts,placements,60,35,99,3)
        self.assertEqual(len({(p.object_id,p.instance_id) for p in placements}),4)

    def test_holes_are_not_free_space_and_defaults(self):
        p=part(1,[(0,0),(20,0),(20,20),(0,20)])
        p.contours.append(cam.Contour([(2,2),(18,2),(18,18),(2,18)],True,role='inner'))
        small=part(2,[(0,0),(5,0),(5,5),(0,5)])
        placements,counts=cam.best_contour_nesting([p,small],24,24,2,1,(0,180))
        self.assertEqual(counts,{1:1});self.assertEqual(cam.nesting_offset(p,2),1)
        self.assert_clear([p,small],placements,24,24,2,1)

    def test_reject_invalid_and_accept_no_fit(self):
        p=part(1,[(0,0),(10,0),(10,10),(0,10)])
        for offset in (-1,float('nan'),float('inf')):
            p.nest_offset=offset
            with self.assertRaises(ValueError):cam.best_contour_nesting([p],30,30,2,1,(0,))
        p.nest_offset=0;p.contours[0].closed=False
        with self.assertRaises(ValueError):cam.best_contour_nesting([p],30,30,2,1,(0,))
        p.contours[0].closed=True
        self.assertEqual(cam.best_contour_nesting([p],5,5,2,1,(0,)),([],{}))

    def test_staggered_arm_and_cancel_callback(self):
        p=part(1,[(0,0),(12,0),(12,4),(60,4),(60,10),(12,10),(12,14),(0,14)],8,1.5)
        placements,counts=cam.best_contour_nesting([p],130,90,3,2,(0,180))
        self.assertEqual(counts,{1:8});self.assert_clear([p],placements,130,90,3,2)
        def cancel(*args):raise RuntimeError('cancel')
        with self.assertRaisesRegex(RuntimeError,'cancel'):
            cam.best_contour_nesting([p],130,90,3,2,(0,180),cancel)


if __name__=='__main__':unittest.main()
