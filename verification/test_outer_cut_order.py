import unittest
import cfrp_router_cam as cam
from test_v105_selection_split import config

class OuterCutOrderTests(unittest.TestCase):
    def parts(self):
        def square(x,role,layer,size=20):
            return cam.Contour([(x,0),(x+size,0),(x+size,size),(x,size)],role=role,layer=layer,tabs_enabled=False)
        near=square(0,'outer','NEAR');far=square(100,'outer','FIRST')
        inner=square(105,'inner','HOLE',8)
        far.outer_cut_order=1;near.outer_cut_order=2
        return near,far,inner

    def test_optimizer_respects_outer_ranks_and_inner_first(self):
        near,far,inner=self.parts();near.cut_order=1
        for optimize in (False,True):
            self.assertEqual(cam.ordered_contours([near,far,inner],optimize),[inner,far,near])
        near.outer_cut_order=None
        self.assertEqual(cam.ordered_contours([near,far,inner]),[inner,far,near])
        far.enabled=False
        self.assertNotIn(far,cam.ordered_contours([near,far,inner]))

    def test_generated_nc_and_onion_jobs_keep_sequence(self):
        parts=self.parts();cfg=config();cfg.update(rapid_optimize=True,tool_wear_enabled=False)
        code=cam.generate_gcode(parts,cfg)
        self.assertLess(code.index('layer=HOLE'),code.index('layer=FIRST'))
        self.assertLess(code.index('layer=FIRST'),code.index('layer=NEAR'))
        self.assertIn('order=outer-1',code)
        cfg.update(onion_split=True,onion_split_percent=10,stock=6)
        for _,job in cam.machining_jobs(parts,cfg):
            sequence=cam.ordered_contours(parts,job.get('rapid_optimize',True))
            self.assertEqual([c.layer for c in sequence],['HOLE','FIRST','NEAR'])
            code=cam.generate_gcode(parts,job)
            self.assertTrue(cam.parse_gcode_moves(code))
            self.assertLess(code.index('layer=HOLE'),code.index('layer=FIRST'))
            self.assertLess(code.index('layer=FIRST'),code.index('layer=NEAR'))
            self.assertIn('order=outer-1',code)
