import unittest
import cfrp_router_cam as cam

class FeedPresets(unittest.TestCase):
    def test_user_values_and_no_interpolation(self):
        for thickness,feed in ((2,600),(3,550),(6,500)):
            self.assertEqual(cam.thickness_feed_recommendation(thickness),feed)
        for thickness in (0,2.5,4,5,8,float('nan'),float('inf')):
            self.assertIsNone(cam.thickness_feed_recommendation(thickness))

    def test_rotated_manual_tabs_preserved(self):
        c=cam.Contour([(0,0),(40,0),(40,20),(0,20)],True,tabs=[5,50,95],start_s=15)
        for angle in (0,90,180,37):
            group,_,_=cam.oriented_contour_group([c],angle)
            q=group[0]
            self.assertEqual(q.tabs,c.tabs);self.assertEqual(q.start_s,c.start_s)
            for s in c.tabs:
                a=cam.point_at(c.points,s)[0];b=cam.point_at(q.points,s)[0]
                self.assertAlmostEqual(cam.dist(a,c.points[0]),cam.dist(b,q.points[0]))

if __name__=='__main__':unittest.main()
