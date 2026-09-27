"""Offline preview must not mix machine positions with work coordinates."""
import unittest
import cfrp_router_cam as cam


class PreviewCoordinatesTests(unittest.TestCase):
    def test_machine_park_is_not_a_cut_or_bounds_point(self):
        prefix='G0 X10 Y20 Z5\nG1 Z-6 F500\nG1 X30\nG0 Z5\n'
        for block in ('G53 G0 Z-70\nG53 G0 X605 Y775',
                      'G0 G53 Z-70\nG0 G53 X605 Y775'):
            omitted=[]
            self.assertEqual(cam.parse_gcode_moves(prefix+block,omitted=omitted),cam.parse_gcode_moves(prefix))
            self.assertEqual(len(omitted),2)

    def test_tool_change_has_no_fictional_return_and_preserves_cut(self):
        code=('G0 X10 Y20 Z5\nG1 Z-6 F500\nG1 X30\nG0 Z5\n'
              'M5\nM9\nM881\nG21 G90 G17 G94 G40 G49 G80 G54\nG90 G53 G0 Z-70\n'
              'M8\nS16500 M3\nG4 P3\nG0 X40 Y50\nG0 Z7\nG1 Z-6 F200\nG1 X60 F500')
        moves=cam.parse_gcode_moves(code)
        restarted=[m for m in moves if m.restart]
        self.assertEqual(len(restarted),1)
        self.assertEqual(restarted[0].restart,'공구 교체/매크로')
        self.assertEqual(restarted[0].start,(40.,50.,7.))
        self.assertEqual(restarted[0].end,(40.,50.,-6.))
        self.assertEqual(moves[-1].end,(60.,50.,-6.))
        self.assertFalse(any(m.start[:2]==(30.,20.) and m.end[:2]==(40.,50.) for m in moves))
        self.assertEqual(min(p[2] for m in moves for p in (m.start,m.end)),-6.)

    def test_g53_is_one_block_and_does_not_hide_modal_g0(self):
        moves=cam.parse_gcode_moves('G0 X0 Y0 Z5\nG1 X10 F10\nG0 G53 Z-70\nZ5\nX20')
        self.assertTrue(moves[-1].rapid)
        self.assertEqual(moves[-1].start,(10.,0.,5.))
        self.assertEqual(moves[-1].end,(20.,0.,5.))

    def test_incremental_moves_cannot_resolve_unknown_machine_axis(self):
        moves=cam.parse_gcode_moves('G53 G0 Z-70\nG91 G0 X10 Z5\nG90 Z5\nG1 X20 F100')
        self.assertEqual(len(moves),1)
        self.assertEqual(moves[0].start,(10.,0.,5.))
        self.assertEqual(moves[0].end,(20.,0.,5.))

    def test_offsets_homing_and_probe_words_are_not_cutting_moves(self):
        for command in ('G10 L2 P1 X500 Y700 Z-100','G92 X500 Y700 Z-100',
                        'G28 X0 Y0 Z0','G38.2 Z-100 F50','M6'):
            moves=cam.parse_gcode_moves(command+'\nG90 G0 X10 Y20 Z5\nG1 X30 F500')
            self.assertEqual(len(moves),1,command)
            self.assertEqual(moves[0].start,(10.,20.,5.))
            self.assertEqual(moves[0].end,(30.,20.,5.))
        moves=cam.parse_gcode_moves('G55\nG0 X10 Y20 Z5\nG1 X30')
        self.assertEqual(len(moves),1)

    def test_units_incremental_arcs_and_comments(self):
        moves=cam.parse_gcode_moves('G20 G90 G0 X1 Y0 Z0\nG91 G1 X1 F10\nG21 G90\nG3 X25.4 Y25.4 I-25.4 J0\n(G53 Z-99)\n; M881')
        self.assertEqual(moves[1].end,(50.8,0.,0.))
        self.assertAlmostEqual(moves[1].seconds,6.)
        self.assertAlmostEqual(moves[-1].end[0],25.4)
        self.assertAlmostEqual(moves[-1].end[1],25.4)
        self.assertTrue(all(not m.restart for m in moves))


if __name__=='__main__':unittest.main()
