import math,re,unittest
import cfrp_router_cam as cam
from shapely.geometry import Point,Polygon,LineString
from shapely import union_all
from test_v113_island_pocket import cfg,pocket


def counterbore():
    return cam.Contour(list(Point(10,10).buffer(4,quad_segs=64).exterior.coords)[:-1],
        operation='pocket',role='pocket',target_depth=.5,pocket_max_depth=.5,
        pocket_stock=[(0,0),(20,0),(20,20),(0,20)],tabs_enabled=False)


class PocketCompensationTests(unittest.TestCase):
    def test_counterbore_diameter_correction_and_no_central_ring(self):
        c=counterbore()
        for adjust in (-.1,0,.1):
            settings=cfg(inner_size_adjust=adjust,outer_size_adjust=0)
            target=cam.pocket_target_area(c,2,settings)
            self.assertAlmostEqual(target.bounds[2]-target.bounds[0],8+adjust,delta=.0001)
            rough,finish,_=cam.pocket_plan(c,2,settings)
            swept=union_all([LineString(p+[p[0]]).buffer(1,quad_segs=32) for p in rough+finish])
            self.assertTrue(swept.covers(Point(10,10)))
            # The annulus outside the 3mm through-hole must be cleared too.
            ring=Point(10,10).buffer(3.8).difference(Point(10,10).buffer(1.5))
            self.assertLess(ring.difference(swept).area,.001)
            self.assertLess(swept.difference(target.buffer(.001)).area,.001)

    def test_island_outer_correction_and_open_stock_edge(self):
        c=pocket(False);settings=cfg(inner_size_adjust=.1,outer_size_adjust=.2)
        target=cam.pocket_target_area(c,2,settings)
        self.assertEqual(target.bounds,(0.,0.,40.,30.))
        protected=Polygon(c.pocket_stock).difference(target)
        self.assertAlmostEqual(protected.bounds[0],14.9,places=5)
        rough,finish,_=cam.pocket_plan(c,2,settings)
        schedule,link=cam.pocket_link_schedule(c,rough,finish,2,settings)
        paths=[p+[p[0]] for _,p,_ in schedule]+[p for _,_,p in schedule if p]
        if link:paths.append(link)
        swept=union_all([LineString(p).buffer(1,quad_segs=32) for p in paths])
        self.assertLess(swept.intersection(protected).area,.0001)

    def test_wear_used_by_nc_and_report_and_reset(self):
        c=counterbore();settings=cfg(tool_wear_enabled=True,tool_wear_loss_per_10m=.079,tool_wear_min_d=1.8)
        first,metrics=cam.contour_wear_plan(c,settings,3,.1,0)
        worn,_=cam.contour_wear_plan(c,settings,3,.1,6)
        self.assertLess(first,2);self.assertLess(worn,first)
        code=cam.generate_gcode([c],settings)
        self.assertIn(f'(POCKET TOOL D: {cam.fmt(first)},',code)
        distance=sum(math.dist(m.start[:2],m.end[:2]) for m in cam.parse_gcode_moves(code) if not m.rapid)
        self.assertAlmostEqual(distance,cam.machining_report([c],settings)[0]*1000,delta=.05)
        copies=[counterbore() for _ in range(3)]
        for i,copy in enumerate(copies):
            cam.move_contour_group([copy],(0,0),i*30,0)
        settings.update(tool_change_enabled=True,tool_change_limit_m=metrics[0]/1000*1.1,
                        tool_change_macro='M881',tool_change_return_z=-70,tool_change_dwell=3,z_origin='Bottom')
        changes,planned,loads=cam.tool_replacement_plan(copies,settings,3,.1)
        self.assertEqual(changes,[1,2]);self.assertAlmostEqual(planned[0][0],planned[2][0],places=7)

    def test_correction_guard_and_neighbour_collision(self):
        c=pocket(True)
        for adjust in (math.nan,2,-2):
            with self.assertRaises(ValueError):cam.pocket_plan(c,2,cfg(inner_size_adjust=adjust))
        other=cam.Contour([(40.1,0),(50,0),(50,30),(40.1,30)],role='outer')
        settings=cfg(inner_size_adjust=.1,outer_size_adjust=-.1)
        self.assertTrue(cam.pocket_job_issues([c,other],settings,{id(c):1.9}))


if __name__=='__main__':unittest.main()
