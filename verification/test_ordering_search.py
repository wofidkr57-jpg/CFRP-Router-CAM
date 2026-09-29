"""Faster nearest-path search must preserve the exhaustive machining order."""
import math,random,unittest
from unittest import mock
import cfrp_router_cam as cam


def exhaustive_sequence(contours,current,bounds=None):
    remaining=list(contours);result=[]
    while remaining:
        index=min(range(len(remaining)),key=lambda i:(cam._contour_nearest_point(remaining[i],current)[0],
                                                     abs(remaining[i].area),i))
        c=remaining.pop(index);result.append(c)
        if c.closed:current=cam._contour_nearest_point(c,current)[1]
        elif c.points:current=c.points[-1] if cam.dist(current,c.points[0])<=cam.dist(current,c.points[-1]) else c.points[0]
    return result,current


class OrderingSearchTests(unittest.TestCase):
    def fixtures(self,seed):
        rng=random.Random(seed);contours=[]
        for i in range(16):
            x,y=rng.uniform(-150,150),rng.uniform(-150,150)
            r=rng.uniform(.3,12);n=rng.randint(8,90)
            c=cam.Contour([(x+r*math.cos(j*2*math.pi/n),y+r*math.sin(j*2*math.pi/n)) for j in range(n)],
                          role='inner' if i%3 else 'outer',closed=i%7!=0,object_id=1,instance_id=i+1)
            c.enabled=i%11!=0
            if i%3==1:
                inner=cam.Contour([(x+r/3*math.cos(j*2*math.pi/n),y+r/3*math.sin(j*2*math.pi/n)) for j in range(n)],
                                  role='inner',object_id=1,instance_id=i+1)
                contours.append(inner)
            contours.append(c)
        return contours

    def test_sequences_match_exhaustive_paths_and_return_positions(self):
        for seed in range(12):
            contours=self.fixtures(seed);start=(seed*13.,seed*-7.)
            for subset in (contours,[c for c in contours if c.closed],[c for c in contours if not c.closed]):
                expected,end=exhaustive_sequence(subset,start)
                actual,actual_end=cam._nearest_contour_sequence(subset,start)
                self.assertEqual([id(c) for c in actual],[id(c) for c in expected])
                self.assertEqual(actual_end,end)

    def test_complete_order_matches_unpruned_search_with_manual_ranks(self):
        for seed in range(12):
            contours=self.fixtures(seed)
            if seed%2:contours[3].cut_order=1
            if seed%3==0:
                for i,c in enumerate(c for c in contours if c.closed and c.role=='outer'):c.outer_cut_order=9-i
            actual=cam.ordered_contours(contours,True,(11.,-8.))
            def exhaustive_distance(c,current,bounds,best):
                return cam._contour_nearest_point(c,current)[0]
            with mock.patch.object(cam,'_ordering_distance',side_effect=exhaustive_distance), \
                 mock.patch.object(cam,'_nearest_contour_sequence',side_effect=exhaustive_sequence):
                expected=cam.ordered_contours(contours,True,(11.,-8.))
            self.assertEqual([id(c) for c in actual],[id(c) for c in expected])

    def test_ties_empty_degenerate_and_enclosing_boxes(self):
        contours=[cam.Contour([(0.,0.),(1.,0.),(1.,1.),(0.,1.)]),
                  cam.Contour([(0.,0.),(2.,0.),(2.,2.),(0.,2.)]),
                  cam.Contour([(0.,0.),(1.,0.),(1.,1.),(0.,1.)]),
                  cam.Contour([(0.,0.),(0.,0.)]),cam.Contour([],closed=False)]
        for start in ((0.,0.),(.5,.5),(10.,10.)):
            actual,end=cam._nearest_contour_sequence(contours,start)
            expected,expected_end=exhaustive_sequence(contours,start)
            self.assertEqual([id(c) for c in actual],[id(c) for c in expected]);self.assertEqual(end,expected_end)

    def test_distant_dense_candidates_are_pruned(self):
        cs=[cam.Contour([(i*100+math.cos(j*2*math.pi/512),math.sin(j*2*math.pi/512)) for j in range(512)])
            for i in range(20)]
        original=cam.nearest_path_distance
        with mock.patch.object(cam,'nearest_path_distance',wraps=original) as nearest:
            result,_=cam._nearest_contour_sequence(cs,(-2.,0.))
            self.assertEqual([id(c) for c in result],[id(c) for c in cs])
            self.assertLess(nearest.call_count,80)  # Exhaustive search performs 230 full scans.

    def test_feature_bundles_preserve_concentric_and_instance_boundaries(self):
        cs=self.fixtures(18)
        expected=cam._inner_feature_bundles(cs)
        original=cam._same_inner_feature
        with mock.patch.object(cam,'_same_inner_feature',side_effect=lambda a,b,features=None:original(a,b)):
            exhaustive=cam._inner_feature_bundles(cs)
        self.assertEqual([[id(c) for c in g] for g in expected],[[id(c) for c in g] for g in exhaustive])
