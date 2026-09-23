"""Offline replacement planning and NC sequencing; never communicates with Mach3."""
import math
import unittest
import cfrp_router_cam as cam
from test_v105_selection_split import config


def cfg(**changes):
    value=config()
    value.update(z_origin='Bottom', stock=6., tool_d=2., tool_change_enabled=True,
                 tool_change_limit_m=8., tool_change_macro='M881', tool_change_return_z=-70.,
                 tool_change_dwell=3., m8_enabled=True, tool_wear_enabled=True,
                 tool_wear_loss_per_10m=.079, tool_wear_min_d=1.9,
                 start_code='G21 G90 G17 G54\nS{RPM} M3', end_code='G0 Z{SAFE_Z}\nM5\nM9\nM30')
    value.update(changes)
    return value


def lines(n=18):
    return [cam.Contour([(0.,i*10.),(1000.,i*10.)],closed=False) for i in range(n)]


class ToolReplacementTests(unittest.TestCase):
    def test_balanced_18m_and_no_last_change(self):
        for limit in (6.,6.5,8.):
            self.assertEqual(cam.balanced_tool_groups([1.]*18,limit),[(0,6),(6,12),(12,18)])
        self.assertEqual(cam.balanced_tool_groups([2.,4.],6.),[(0,2)])
        self.assertEqual(cam.balanced_tool_groups([],6.),[])
        self.assertEqual(cam.balanced_tool_groups([0.,0.],6.),[(0,2)])

    def test_indivisible_contours_preserve_order_and_limit(self):
        weights=[4.,4.,4.]
        self.assertEqual(cam.balanced_tool_groups(weights,6.),[(0,1),(1,2),(2,3)])
        for weights in ([0.,2.,0.,5.,1.,6.],[3.,2.,3.,2.,3.],[6.,.001,6.]):
            groups=cam.balanced_tool_groups(weights,6.)
            self.assertEqual([i for a,b in groups for i in range(a,b)],list(range(len(weights))))
            self.assertTrue(all(sum(weights[a:b])<=6.+cam.EPS for a,b in groups))
        for weights,limit in (([7.],6.),([1.],0.),([math.nan],6.),([-1.],6.)):
            with self.assertRaises(ValueError):cam.balanced_tool_groups(weights,limit)

    def test_wear_resets_and_report_matches(self):
        changes,plan,loads=cam.tool_replacement_plan(lines(),cfg(),6.,.1)
        self.assertEqual(changes,[6,12]);self.assertEqual(loads,[6.,6.,6.])
        self.assertEqual(plan[0][0],plan[6][0]);self.assertEqual(plan[0][0],plan[12][0])
        self.assertLess(plan[5][0],plan[0][0])
        self.assertAlmostEqual(cam.machining_report(lines(),cfg())[0],18.)
        code=cam.generate_gcode(lines(),cfg())
        self.assertIn('(TOOL_DIAMETER_JOB_END_MM: 1.9526)',code)

    def assert_resume_sequence(self,code):
        chunks=code.split('\nM881\n')
        self.assertGreater(len(chunks),1)
        for chunk in chunks[1:]:
            commands=[s for s in chunk.splitlines() if s and not s.startswith('(')]
            self.assertEqual(commands[:5],['G21 G90 G17 G94 G40 G49 G80 G54','G90 G53 G0 Z-70','M8','S18000 M3','G4 P3'])
            self.assertTrue(commands[5].startswith('G0 X'),commands[:8])
            self.assertTrue(commands[6].startswith('G0 Z'),commands[:8])
            self.assertNotIn('G10',chunk)

    def test_nc_retract_macro_xy_then_z_and_no_extra_stop(self):
        code=cam.generate_gcode(lines(),cfg())
        self.assertEqual(code.count('\nM881\n'),2)
        self.assertEqual(code.count('\nM30'),1)
        self.assertIn('BEFORE CONTOUR 7',code);self.assertIn('BEFORE CONTOUR 13',code)
        self.assertEqual(code.count('G90 G0 Z11\nM5\nM9\nM881'),2)
        self.assert_resume_sequence(code)
        self.assertNotIn('M881',cam.generate_gcode(lines(6),cfg(tool_change_limit_m=6.)))

    def test_disabled_preserves_single_tool_plan(self):
        changes,plan,loads=cam.tool_replacement_plan(lines(),cfg(tool_change_enabled=False),6.,.1)
        self.assertEqual(changes,[]);self.assertEqual(loads,[18.])
        self.assertLess(plan[12][0],plan[0][0])
        self.assertNotIn('M881',cam.generate_gcode(lines(),cfg(tool_change_enabled=False)))

    def test_pocket_return_and_cut_distance(self):
        pockets=[cam.Contour([(x,0.),(x+20.,0.),(x+20.,20.),(x,20.)],
                             operation='pocket',role='pocket',target_depth=.5,pocket_max_depth=.5,
                             tabs_enabled=False) for x in (0.,30.,60.)]
        settings=cfg(pocket_stepover=40.,pocket_stepdown=.25,pocket_finish=.1,pocket_stay_down=True,tool_wear_enabled=False)
        length=cam.contour_cut_metrics(pockets[0],settings,6.,.1,2.)[0]/1000
        settings['tool_change_limit_m']=length*1.1
        code=cam.generate_gcode(pockets,settings)
        self.assertEqual(code.count('\nM881\n'),2)
        self.assert_resume_sequence(code)
        cut=sum(math.dist(m.start[:2],m.end[:2]) for m in cam.parse_gcode_moves(code) if not m.rapid)/1000
        self.assertAlmostEqual(cut,cam.machining_report(pockets,settings)[0],places=4)

    def test_invalid_machine_settings_rejected(self):
        for changes in ({'z_origin':'Top'},{'tool_change_macro':'M881 P99'},
                        {'tool_change_macro':'M881\nG0 X0'}, {'tool_change_return_z':0.},
                        {'tool_change_return_z':math.nan},{'tool_change_dwell':-1.},
                        {'tool_change_limit_m':.5}):
            with self.subTest(changes=changes),self.assertRaises(ValueError):
                cam.generate_gcode(lines(2),cfg(**changes))

    def test_split_rough_finish_and_manual_outer_order(self):
        contours=[]
        for i in range(3):
            c=cam.Contour([(i*400.,0.),(i*400.+250.,0.),(i*400.+250.,250.),(i*400.,250.)],closed=True,role='outer')
            c.outer_cut_order=3-i;contours.append(c)
        settings=cfg(onion_split=True,onion_split_percent=10.,tool_change_limit_m=1.1)
        for name,job in cam.machining_jobs(contours,settings):
            ordered=cam.ordered_contours(cam.stage_contours(contours,job),False,(0.,0.))
            self.assertEqual([c.outer_cut_order for c in ordered],[1,2,3])
            changes,plan,loads=cam.tool_replacement_plan(ordered,job,6.,.1)
            self.assertEqual(changes,[1,2]);self.assertTrue(all(v<=1.1 for v in loads))
            code=cam.generate_gcode(contours,job)
            self.assertEqual(code.count('\nM881\n'),2)
            self.assert_resume_sequence(code)
        with self.assertRaises(ValueError):
            cam.generate_gcode(contours,cfg(wall_finish=True))


if __name__=='__main__':unittest.main()
