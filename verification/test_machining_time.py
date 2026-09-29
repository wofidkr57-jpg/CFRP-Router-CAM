import math
import unittest
import cfrp_router_cam as cam
from test_v105_selection_split import config, square


class MachiningTimeTests(unittest.TestCase):
    def test_xyz_rapid_and_fixed_wait_are_added_before_display_rounding(self):
        estimate=cam.job_time_estimate('G21 G90\nG0 X300 Y400 Z1200\nG1 X500 F100\nG0 Z0\nG4 P5',10)
        self.assertAlmostEqual(estimate.rapid_mm,2500)
        self.assertAlmostEqual(estimate.rapid_minutes,2500/3000)
        self.assertAlmostEqual(estimate.margin_minutes,(10+2500/3000)*.1)
        self.assertAlmostEqual(estimate.total_minutes,(10+2500/3000)*1.1+5/60)

    def test_machine_and_macro_travel_are_not_invented(self):
        code='G0 X10 Z5\nG53 G0 Z-700\nG0 Z5\nG0 X20\nM881\nG0 X999 Y999\nG0 Z10\nG1 Z-2 F1000'
        estimate=cam.job_time_estimate(code,1)
        self.assertAlmostEqual(estimate.rapid_mm,math.hypot(10,5)+10)
        self.assertEqual(estimate.unestimated_moves,5)
        self.assertTrue(estimate.external_wait)
        self.assertIn('ADD EXTERNAL WAIT/TRAVEL','\n'.join(cam.time_estimate_header(estimate)))

    def test_units_incremental_motion_and_modal_rapid(self):
        estimate=cam.job_time_estimate('G21 G90\nG0 X30\nG91 Z40\nG20 G90 X2',0)
        self.assertAlmostEqual(estimate.rapid_mm,30+40+20.8)

    def test_arc_and_extra_feed_moves_count_without_chord_shortcut(self):
        estimate=cam.job_time_estimate('G21 G90\nG0 X10 Y0\nG3 X10 Y0 Z-6 I-10 J0 F100',0)
        self.assertAlmostEqual(estimate.cutting_minutes,math.hypot(20*math.pi,6)/100)
        self.assertAlmostEqual(estimate.rapid_mm,10)

    def test_known_generated_retract_and_approach_match_hand_calculation(self):
        settings=config()
        contour=cam.Contour([(0,0),(30,0)],closed=False)
        base=cam.machining_report([contour],settings,include_rapid=False)
        code=cam.generate_gcode([contour],settings)
        estimate=cam.job_time_estimate(code,base[1])
        self.assertAlmostEqual(base[0],.03)
        self.assertAlmostEqual(base[1],30/600+3.1/150)
        self.assertAlmostEqual(estimate.rapid_mm,5+4+7.1)
        expected=(base[1]+16.1/3000)*1.1+1/60
        self.assertAlmostEqual(cam.machining_report([contour],settings)[1],expected)
        self.assertIn(f'(This job estimated machining time: {cam.filename_minutes(expected)} min - rounded up)',code)

    def test_farther_holes_and_higher_safe_z_increase_time_not_wear_distance(self):
        def report(gap,safe):
            contours=[cam.Contour([(0,0),(10,0)],closed=False),cam.Contour([(gap,0),(gap+10,0)],closed=False)]
            return cam.machining_report(contours,dict(config(),safe_z=safe))
        near=report(20,5);far=report(3020,5);higher=report(20,25)
        self.assertEqual(near[0],far[0]);self.assertEqual(near[0],higher[0])
        self.assertAlmostEqual(far[1]-near[1],1.1)
        self.assertGreater(higher[1],near[1])

    def test_preflight_is_included_and_does_not_add_cutting_distance(self):
        contours=[square(0,0,40,30)]
        settings=config()
        normal=cam.machining_report(contours,settings)
        preview=cam.machining_report(contours,dict(settings,preflight_enabled=True,preflight_z=30,preflight_feed=100))
        self.assertEqual(normal[0],preview[0])
        self.assertGreater(preview[1]-normal[1],1.4)

    def test_split_programs_have_independent_total_times(self):
        contours=[square(0,0,40,30)]
        settings=dict(config(),stock=6,onion_split=True,onion_split_percent=10)
        for name,job in cam.machining_jobs(contours,settings):
            code=cam.generate_gcode(contours,job)
            distance,total=cam.machining_report(contours,job)
            base=cam.machining_report(contours,job,include_rapid=False)[1]
            self.assertGreater(total,base*1.1)
            self.assertIn(f'estimated machining time: {cam.filename_minutes(total)} min',code)
            self.assertIn('(TIME_MARGIN_PERCENT: 10)',code)
            self.assertGreater(distance,0)

    def test_rounding_never_reduces_fractional_minutes(self):
        for value,expected in ((0,1),(9.4,10),(12.4,13),(22.6,23),(35,35)):
            self.assertEqual(cam.filename_minutes(value),expected)

    def test_comments_and_manual_wait_do_not_become_motion_or_duration(self):
        estimate=cam.job_time_estimate('(G0 X999; G4 P900)\nM0\nG0 X30 ; G0 Z999\nG4 P2',1)
        self.assertEqual(estimate.rapid_mm,30)
        self.assertEqual(estimate.dwell_seconds,2)
        self.assertTrue(estimate.external_wait)
        self.assertAlmostEqual(estimate.total_minutes,(1+.01)*1.1+2/60)


if __name__=='__main__':unittest.main()
