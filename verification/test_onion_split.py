import math
import unittest
import cfrp_router_cam as cam
from test_v105_selection_split import config


def outer():
    c=cam.Contour([(100,200),(140,200),(140,230),(100,230)],closed=True,role='outer')
    c.tabs=[10,35];c.tabs_enabled=True
    return c


class OnionSplitTests(unittest.TestCase):
    def cfg(self,**kw):
        result=config()
        result.update(stock=6.0,tool_d=2.0,onion_split=True,onion_split_percent=10,
                      tab_count=3,finish_allowance=.12,rapid_optimize=False)
        result.update(kw)
        return result

    def test_floor_wall_tabs_and_independent_programs(self):
        for origin in ('Top','Bottom'):
            for passes in (1,3):
                with self.subTest(origin=origin,passes=passes):
                    contours=[outer()]
                    cfg=self.cfg(z_origin=origin,full_depth=passes==1,passes=passes,
                                 start_code='G21\nG90\nG54\nM0 (CHANGE TOOL)\nS{RPM} M3',
                                 end_code='G0 Z{SAFE_Z}\nM5\nM30')
                    jobs=cam.machining_jobs(contours,cfg)
                    self.assertEqual([j[0] for j in jobs],['ROUGH','FINISH'])
                    codes=[cam.generate_gcode(contours,c) for _,c in jobs]
                    shift=6 if origin=='Bottom' else 0
                    for index,code in enumerate(codes):
                        self.assertEqual(code.count('M0 (CHANGE TOOL)'),1)
                        self.assertEqual(code.count('M30'),1)
                        self.assertIn('tabs=0',code)
                        self.assertIn('(ONION_SKIN_REMAINING_MM: 0.6)',code)
                        moves=cam.parse_gcode_moves(code)
                        self.assertAlmostEqual(min(m.end[2] for m in moves),shift-(5.4 if index==0 else 6.1))
                        cut=[m for m in moves if not m.rapid and m.start[:2]!=m.end[:2]]
                        # Outer rough leaves .12 mm radial stock; finish is nominal.
                        self.assertAlmostEqual(min(min(m.start[0],m.end[0]) for m in cut),-1.12 if index==0 else -1.0)
                        report=cam.machining_report(contours,jobs[index][1])
                        distance=sum(math.dist(m.start[:2],m.end[:2]) for m in cut)/1000
                        self.assertAlmostEqual(report[0],distance,places=6)
                    self.assertNotIn('(Finish contour',codes[0])
                    self.assertIn('(Finish contour',codes[1])
                    self.assertNotIn('rough - axial',codes[1])
                    self.assertEqual(contours[0].tabs,[10,35])

    def test_overrides_are_finish_only_and_each_blank_falls_back(self):
        for start,end in (('',''),('M0\nS{RPM} M3',''),('','M5\nM2'),('M0','M2')):
            cfg=self.cfg(onion_start_code=start,onion_end_code=end)
            rough,finish=[c for _,c in cam.machining_jobs([outer()],cfg)]
            self.assertEqual(rough['start_code'],cfg['start_code'])
            self.assertEqual(rough['end_code'],cfg['end_code'])
            self.assertEqual(finish['start_code'],start or cfg['start_code'])
            self.assertEqual(finish['end_code'],end or cfg['end_code'])

    def test_fresh_wear_and_full_job_origin_when_finish_subset_differs(self):
        contours=[cam.Contour([(0,0),(10,0)],closed=False),outer()]
        cfg=self.cfg(tool_wear_enabled=True,tool_wear_loss_per_10m=.079,tool_wear_min_d=1)
        for name,job in cam.machining_jobs(contours,cfg):
            code=cam.generate_gcode(contours,job)
            self.assertIn('(TOOL_DIAMETER_JOB_START_MM: 2)',code)
            self.assertIn('(XY_ORIGIN_SOURCE_X_MM: 0)',code)
            if name=='FINISH':
                self.assertEqual(len(cam.stage_contours(contours,job)),1)
                cut=[m for m in cam.parse_gcode_moves(code) if not m.rapid and m.start[:2]!=m.end[:2]]
                self.assertGreater(min(m.end[0] for m in cut),98)

    def test_off_preserves_original_program_and_invalid_split_is_rejected(self):
        cfg=self.cfg(onion_split=False)
        self.assertEqual(cam.machining_jobs([outer()],cfg),[('FULL',cam.resolved_z_config(cfg))])
        for percent in (0,100,-1,float('nan')):
            with self.assertRaises(ValueError):cam.machining_jobs([outer()],self.cfg(onion_split_percent=percent))
        with self.assertRaises(ValueError):
            cam.machining_jobs([cam.Contour([(0,0),(1,0)],closed=False)],self.cfg())


if __name__=='__main__':unittest.main()
