"""Outer visit order: radial bands, CW/CCW, inner-first and manual overrides."""
import copy,math,re,unittest
from test_v105_selection_split import config
import cfrp_router_cam as cam


def part(x,y,name,object_id=1,instance_id=1):
    return cam.Contour([(x-3,y-3),(x+3,y-3),(x+3,y+3),(x-3,y+3)],role='outer',
                       forced_role='outer',layer=name,object_id=object_id,instance_id=instance_id,
                       tabs_enabled=False)


def array():
    return [part(x,y,f'{x}:{y}',1,i+1) for i,(x,y) in enumerate((x,y) for y in (-20.,0.,20.) for x in (-20.,0.,20.))]


class CenterOutOrderTests(unittest.TestCase):
    def test_center_then_perimeter_both_directions(self):
        cs=array();before=copy.deepcopy(cs)
        for rapid in (False,True):
            cw=cam.ordered_contours(cs,rapid,outer_order='center_cw',sheet_center=(0.,0.))
            ccw=cam.ordered_contours(cs,rapid,outer_order='center_ccw',sheet_center=(0.,0.))
            self.assertEqual([c.layer for c in cw],['0.0:0.0','0.0:20.0','20.0:20.0','20.0:0.0','20.0:-20.0','0.0:-20.0','-20.0:-20.0','-20.0:0.0','-20.0:20.0'])
            self.assertEqual([c.layer for c in ccw],[cw[0].layer,cw[1].layer]+[c.layer for c in reversed(cw[2:])])
        self.assertEqual(cs,before)  # No reversal of cutting direction/start/tabs.

    def test_multilayer_array_and_two_columns(self):
        cs=[part(x,y,str((x,y)),i%3+1,i+1) for i,(x,y) in enumerate((x,y) for y in (-40.,-20.,0.,20.,40.) for x in (-40.,-20.,0.,20.,40.))]
        ordered=cam.ordered_contours(cs,outer_order='center_cw',sheet_center=(0.,0.))
        radii=[math.hypot(*cam._contour_center(c)) for c in ordered]
        self.assertEqual(radii[0],0)
        self.assertTrue(all(r<40 for r in radii[:9]));self.assertTrue(all(r>=40 for r in radii[9:]))
        columns=[part(x,y,str((x,y)),1,i+1) for i,(x,y) in enumerate((x,y) for y in (-60.,-40.,-20.,0.,20.,40.,60.) for x in (-20.,20.))]
        seq=cam.ordered_contours(columns,outer_order='center_ccw',sheet_center=(0.,0.))
        self.assertTrue(all(abs(cam._contour_center(c)[1])<=20 for c in seq[:6]))
        self.assertTrue(all(abs(cam._contour_center(c)[1])==60 for c in seq[-4:]))

    def test_inner_pocket_open_before_outer_manual_ranks_win(self):
        cs=array();cs[2].outer_cut_order=1;cs[0].outer_cut_order=2;cs[5].cut_order=1
        inner=part(0,0,'HOLE');inner.role='inner'
        pocket=part(0,0,'POCKET');pocket.operation='pocket';pocket.role='pocket';pocket.target_depth=1.
        opened=cam.Contour([(-2.,-2.),(2.,2.)],closed=False,layer='OPEN')
        cs[-1].enabled=False
        for mode in ('center_cw','center_ccw'):
            seq=cam.ordered_contours(cs+[inner,pocket,opened],outer_order=mode,sheet_center=(0.,0.))
            self.assertEqual(seq[0].layer,'POCKET')
            self.assertLess(seq.index(inner),seq.index(cs[2]));self.assertLess(seq.index(opened),seq.index(cs[2]))
            self.assertEqual([c.layer for c in seq if c.closed and c.role=='outer'][:3],[cs[2].layer,cs[0].layer,cs[5].layer])
            self.assertNotIn(cs[-1],seq)

    def test_translation_rotation_coincident_and_single_contours(self):
        cs=array();expected=[c.layer for c in cam.ordered_contours(cs,outer_order='center_cw',sheet_center=(0.,0.))]
        moved=copy.deepcopy(cs)
        for c in moved:c.points=[(x+500,y-1234) for x,y in c.points]
        self.assertEqual([c.layer for c in cam.ordered_contours(moved,outer_order='center_cw',sheet_center=(500.,-1234.))],expected)
        self.assertEqual(cam.ordered_contours([],outer_order='center_cw',sheet_center=(0.,0.)),[])
        self.assertEqual(cam.ordered_contours(cs[:1],outer_order='center_ccw',sheet_center=(0.,0.)),cs[:1])
        copies=[copy.deepcopy(cs[4]) for _ in range(4)]
        for i,c in enumerate(copies):c.layer=str(i)
        self.assertEqual([c.layer for c in cam.ordered_contours(copies,outer_order='center_cw',sheet_center=(0.,0.))],['0','1','2','3'])
        # A pre-arrayed file with a shared instance id still visits each external
        # component by position rather than treating the entire file as one part.
        for c in cs:c.instance_id=1
        self.assertEqual([c.layer for c in cam.ordered_contours(cs,outer_order='center_cw',sheet_center=(0.,0.))],expected)

    def test_language_modes_unknown_mode_and_legacy_default(self):
        cs=array()
        for value in ('center_cw','중앙 → 바깥 (시계)','Center outward (CW)'):self.assertEqual(cam.outer_order_mode(value),'center_cw')
        self.assertEqual(cam.outer_order_mode('중앙 → 바깥 (반시계)'),'center_ccw')
        self.assertEqual(cam.ordered_contours(cs),cam.ordered_contours(cs,outer_order='nearest'))
        for invalid in ('invalid',None,[],4):
            with self.assertRaises(ValueError):cam.ordered_contours(cs,outer_order=invalid)

    def test_nc_report_wear_and_tool_replacement_follow_same_order(self):
        cs=array();
        for c in cs:c.points=[(x+40,y+40) for x,y in c.points]
        cfg=config();cfg.update(sheet_w=80.,sheet_h=80.,tool_d=2.,stock=6.,extra=.2,tool_wear_enabled=True,
                tool_wear_loss_per_10m=.079,tool_wear_min_d=1.9,rapid_optimize=True,
                z_origin='Bottom',tool_change_enabled=True,tool_change_limit_m=.08,
                tool_change_macro='M881',tool_change_return_z=-70.,tool_change_dwell=3.)
        for mode in ('center_cw','center_ccw'):
            cfg['outer_order_mode']=mode
            seq=cam.ordered_contours(cs,True,outer_order=mode,sheet_center=(40.,40.))
            code=cam.generate_gcode(cs,dict(cfg))
            labels=re.findall(r'\(Contour \d+: .*?layer=([^,]+)',code)
            self.assertEqual(labels,[c.layer for c in seq])
            self.assertIn(f'(OUTER_ORDER_MODE: {mode.upper()})',code)
            self.assertIn('\nM881\n',code)
            cuts,plan,loads=cam.tool_replacement_plan(seq,cfg,6.,.2)
            report=cam.machining_report(cs,cfg,include_rapid=False)
            self.assertAlmostEqual(report[0],sum(loads),places=8)
            self.assertTrue(all(v<=.08+cam.EPS for v in loads))
            self.assertEqual([cam.fmt(d) for d,metrics in plan],re.findall(r'\(Contour \d+: .*?tool_d=([0-9.]+)',code))
            self.assertTrue(cam.parse_gcode_moves(code))

    def test_onion_finish_files_keep_center_out_order_and_cut_direction(self):
        cs=array();
        for c in cs:c.points=[(x+40,y+40) for x,y in c.points]
        cfg=config();cfg.update(sheet_w=80.,sheet_h=80.,tool_d=2.,stock=6.,extra=.2,rapid_optimize=False,
                                            onion_split=True,onion_split_percent=10,tool_wear_enabled=False)
        for mode in ('center_cw','center_ccw'):
            cfg['outer_order_mode']=mode
            expected=[c.layer for c in cam.ordered_contours(cs,False,outer_order=mode,sheet_center=(40.,40.))]
            for label,job in cam.machining_jobs(cs,cfg):
                code=cam.generate_gcode(cs,dict(job))
                self.assertEqual(re.findall(r'\(Contour \d+: .*?layer=([^,]+)',code),expected)
        # Changing visit direction must not reverse any individual cutting loop.
        def cuts(code):
            blocks=re.split(r'\(Contour \d+: .*?layer=([^,]+).*?\)\n',code)
            return {blocks[i]:[line for line in blocks[i+1].splitlines() if line.startswith(('G1 X','G2 X','G3 X'))]
                    for i in range(1,len(blocks),2)}
        cfg['onion_split']=False
        cfg['outer_order_mode']='center_cw';cw=cam.generate_gcode(cs,dict(cfg))
        cfg['outer_order_mode']='center_ccw';ccw=cam.generate_gcode(cs,dict(cfg))
        self.assertEqual(cuts(cw),cuts(ccw))

    def test_off_center_parts_use_entire_sheet_not_part_bounds(self):
        cs=[part(x,40.,str(x)) for x in (20.,60.,100.)]
        for mode in ('center_cw','center_ccw'):
            self.assertEqual([c.layer for c in cam.ordered_contours(cs,outer_order=mode,sheet_center=(120.,40.))],
                             ['100.0','60.0','20.0'])
            self.assertEqual([c.layer for c in cam.ordered_contours(cs,outer_order=mode,sheet_center=(60.,40.))],
                             ['60.0','100.0','20.0'] if mode=='center_cw' else ['60.0','20.0','100.0'])
            cs[0].outer_cut_order=1
            self.assertEqual([c.layer for c in cam.ordered_contours(cs,outer_order=mode,sheet_center=(120.,40.))],
                             ['20.0','100.0','60.0'])
            cs[0].outer_cut_order=None

    def test_sheet_center_validation_and_no_implicit_layout_center(self):
        self.assertEqual(cam.sheet_center_from_config({'sheet_w':240.,'sheet_h':80.}),(120.,40.))
        for key in ('sheet_w','sheet_h'):
            for bad in (0,-1,float('nan'),float('inf'),None,'bad'):
                cfg={'sheet_w':240.,'sheet_h':80.,'outer_order_mode':'center_cw'};cfg[key]=bad
                with self.assertRaises(ValueError):cam.ordering_sheet_center(cfg)
                cfg.update(config());cfg['outer_order_mode']='center_cw'
                with self.assertRaises(ValueError):cam.generate_gcode([part(100,40,'P')],cfg)
        with self.assertRaises(ValueError):cam.ordered_contours(array(),outer_order='center_cw')
        with self.assertRaises(ValueError):cam.ordering_sheet_center({'outer_order_mode':'center_cw'})
        self.assertIsNone(cam.ordering_sheet_center({}))  # Legacy nearest needs no sheet settings.

    def test_sheet_order_is_independent_of_work_origin_and_updates_nc(self):
        cs=[part(x,40.,str(x)) for x in (20.,60.,100.)]
        cfg=config();cfg.update(sheet_w=240.,sheet_h=80.,outer_order_mode='center_cw',tool_wear_enabled=False)
        for origin in ('DXF 원점','좌하단','중앙'):
            cfg['xy_origin']=origin
            for override in (None,(7.,13.)):
                cfg['_xy_origin_override']=override
                code=cam.generate_gcode(cs,dict(cfg))
                self.assertEqual(re.findall(r'\(Contour \d+: .*?layer=([^,]+)',code),['100.0','60.0','20.0'])
                self.assertIn('(OUTER_ORDER_REFERENCE: SHEET_CENTER)',code)
                self.assertIn('(OUTER_ORDER_CENTER_SOURCE_X_MM: 120)',code)
                self.assertIn('(OUTER_ORDER_CENTER_SOURCE_Y_MM: 40)',code)
                self.assertTrue(cam.parse_gcode_moves(code))
        cfg['sheet_w']=120.
        code=cam.generate_gcode(cs,cfg)
        self.assertEqual(re.findall(r'\(Contour \d+: .*?layer=([^,]+)',code),['60.0','100.0','20.0'])
