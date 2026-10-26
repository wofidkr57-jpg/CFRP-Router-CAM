"""Offline geometry and Z-depth checks for the simplified machining workflow."""
import copy
from dataclasses import asdict
import json
import math
from pathlib import Path
import sys
from types import SimpleNamespace
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import cfrp_router_cam as cam
from test_v111_wear_array_order import config


def cfg(**values):
    result=config()
    result.update(stock=3.0,tool_wear_enabled=False,tool_d=2.0,
                  pocket_stepover=40.0,pocket_stepdown=.25,pocket_finish=.1)
    result.update(values)
    return result


def outer(**values):
    return cam.Contour([(0.,0.),(30.,0.),(30.,20.),(0.,20.)],**values)


class Value:
    def __init__(self,value):self.value=value
    def get(self):return self.value
    def set(self,value):self.value=value


class TouchGeometryTests(unittest.TestCase):
    def test_arbitrary_rotation_preserves_features_and_other_instances(self):
        selected=cam.Contour([(10.,20.),(22.,20.),(14.,27.)],object_id=2,instance_id=3,
                             tabs=[2.,8.],start_s=3.,bridges=[((11.,20.),(12.,20.))],
                             pocket_holes=[[(12.,21.),(13.,21.),(12.,22.)]],
                             pocket_stock=[(10.,20.),(22.,20.),(14.,27.)],
                             target_depth=1.2,additional_depth=.3,cut_order=4)
        other=copy.deepcopy(selected);other.instance_id=4
        other_object=copy.deepcopy(selected);other_object.object_id=3
        before=copy.deepcopy(selected);others=copy.deepcopy([other,other_object])
        angle=37.;r=math.radians(angle);ca,sa=math.cos(r),math.sin(r)
        def rotated(point):
            x,y=point[0]-16.,point[1]-23.5
            return 16.+x*ca-y*sa,23.5+x*sa+y*ca
        self.assertEqual(cam.rotate_contour_group([selected,other,other_object],(2,3),angle),1)
        for old,new in zip(before.points,selected.points):
            self.assertAlmostEqual(new[0],rotated(old)[0]);self.assertAlmostEqual(new[1],rotated(old)[1])
        self.assertAlmostEqual(selected.area,before.area)
        self.assertEqual(selected.tabs,before.tabs);self.assertEqual(selected.start_s,before.start_s)
        self.assertEqual((selected.target_depth,selected.additional_depth,selected.cut_order),(1.2,.3,4))
        self.assertEqual(selected.bridges,[(rotated(a),rotated(b)) for a,b in before.bridges])
        self.assertEqual(selected.pocket_holes,[[rotated(p) for p in ring] for ring in before.pocket_holes])
        self.assertEqual(selected.pocket_stock,[rotated(p) for p in before.pocket_stock])
        for distance in before.tabs+[before.start_s]:
            expected=rotated(cam.point_at(before.points,distance,True)[0])
            actual=cam.point_at(selected.points,distance,True)[0]
            self.assertAlmostEqual(actual[0],expected[0]);self.assertAlmostEqual(actual[1],expected[1])
        self.assertEqual([other,other_object],others)

    def test_rotation_wrapper_keeps_layout_source_and_per_instance_centres(self):
        first=outer(object_id=1,instance_id=1)
        second=outer(object_id=1,instance_id=2)
        cam.move_contour_group([second],(1,2),70,10)
        untouched=outer(object_id=2,instance_id=1)
        cam.move_contour_group([untouched],(2,1),140,0)
        state=SimpleNamespace(contours=[first,second,untouched],nest_active=False,nest_source=None,
                              preview_cache={'old':1},collision_cache_key='old',status=Value(''))
        state.selected_instance_keys=lambda:{(1,1),(1,2)}
        snapshots=[];synced=[];redraw=[]
        state.push_undo=lambda label:snapshots.append(copy.deepcopy(state.contours))
        state.sync_part_sources_from_preview=lambda:synced.append(True)
        state.redraw=lambda **kw:redraw.append(kw)
        before=copy.deepcopy(state.contours)
        self.assertEqual(cam.App.rotate_selected_instances(state,90),2)
        self.assertEqual(snapshots,[before]);self.assertEqual(state.nest_source,before)
        self.assertTrue(state.nest_active);self.assertEqual(synced,[True])
        self.assertEqual(untouched,before[2]);self.assertFalse(state.preview_cache)
        for key,centre in (((1,1),(15.,10.)),((1,2),(85.,20.))):
            x0,y0,x1,y1=cam.contour_group_bounds(state.contours,key)
            self.assertEqual(((x0+x1)/2,(y0+y1)/2),centre)
        saved=copy.deepcopy(state.nest_source)
        cam.App.rotate_selected_instances(state,17,keys={(1,2)})
        self.assertEqual(state.nest_source,saved);self.assertEqual(synced,[True])

    def test_old_contour_files_default_to_zero_extra_and_new_values_round_trip(self):
        original=outer(target_depth=1.0)
        data=json.loads(json.dumps(asdict(original)));data.pop('additional_depth')
        loaded=cam.decode_job_value(data,cam.Contour)
        self.assertEqual(loaded.additional_depth,0.0)
        self.assertEqual(cam.generate_gcode([loaded],cfg()),cam.generate_gcode([original],cfg()))
        original.additional_depth=.4
        loaded=cam.decode_job_value(json.loads(json.dumps(asdict(original))),cam.Contour)
        self.assertEqual(loaded.additional_depth,.4);self.assertEqual(loaded.target_depth,1.)
        data['unknown_field']=True
        with self.assertRaises(ValueError):cam.decode_job_value(data,cam.Contour)

    def test_explicit_extra_depth_does_not_change_other_contours(self):
        changed=outer(target_depth=1.,additional_depth=.4)
        original=outer(target_depth=1.)
        self.assertEqual(cam.effective_contour_depth(changed,3,.1),1.4)
        self.assertEqual(cam.effective_contour_depth(original,3,.1),1.)
        code=cam.generate_gcode([changed],cfg())
        moves=cam.parse_gcode_moves(code)
        self.assertAlmostEqual(min(p[2] for m in moves for p in (m.start,m.end)),-1.4)
        self.assertEqual((changed.target_depth,changed.additional_depth),(1.,.4))

    def test_through_extra_retains_tabs_relative_to_material_bottom(self):
        profile=outer(additional_depth=.3,tabs=[5.],tabs_enabled=True)
        settings=cfg(tab_count=1,tab_flat=2.,tab_remain=.2)
        code=cam.generate_gcode([profile],settings)
        cuts=[m for m in cam.parse_gcode_moves(code) if not m.rapid]
        self.assertAlmostEqual(min(p[2] for m in cuts for p in (m.start,m.end)),-3.4)
        self.assertTrue(any(abs(p[2]+2.8)<1e-6 for m in cuts for p in (m.start,m.end)))
        bottom=cam.generate_gcode([profile],dict(settings,z_origin='Bottom'))
        cuts=[m for m in cam.parse_gcode_moves(bottom) if not m.rapid]
        self.assertAlmostEqual(min(p[2] for m in cuts for p in (m.start,m.end)),-.4)
        self.assertTrue(any(abs(p[2]-.2)<1e-6 for m in cuts for p in (m.start,m.end)))

    def test_pocket_extra_retains_imported_floor_and_updates_passes_and_time(self):
        pocket=outer(operation='pocket',role='pocket',target_depth=.5,pocket_max_depth=.5,
                     pocket_stock=[(0.,0.),(30.,0.),(30.,20.),(0.,20.)],tabs_enabled=False)
        old_metrics=cam.contour_cut_metrics(pocket,cfg(),3.,.1,2.)
        pocket.additional_depth=.3
        cam.validate_pocket(pocket,cfg())
        code=cam.generate_gcode([pocket],cfg())
        self.assertIn('depth=0.8',code);self.assertIn('pass 4/4',code)
        self.assertEqual(pocket.pocket_max_depth,.5);self.assertEqual(pocket.target_depth,.5)
        self.assertGreater(cam.contour_cut_metrics(pocket,cfg(),3.,.1,2.)[0],old_metrics[0])
        self.assertAlmostEqual(min(p[2] for m in cam.parse_gcode_moves(code) for p in (m.start,m.end)),-.8)
        pocket.target_depth=.6
        with self.assertRaises(ValueError):cam.validate_pocket(pocket,cfg())
        pocket.target_depth=.5;pocket.additional_depth=2.5
        with self.assertRaises(ValueError):cam.validate_pocket(pocket,cfg())

    def test_invalid_additional_depth_is_not_sent_into_toolpath_math(self):
        for value in (-.1,float('nan'),float('inf')):
            with self.assertRaises(ValueError):cam.generate_gcode([outer(additional_depth=value)],cfg())

    def test_depth_first_order_uses_explicit_extra_depth(self):
        deep=outer(role='inner',target_depth=.5,additional_depth=1.0)
        shallow=outer(role='inner',target_depth=1.)
        cam.move_contour_group([shallow],(0,1),40,0)
        self.assertEqual(cam.ordered_contours([deep,shallow],False,depth_first=True),[shallow,deep])

    def test_step_import_preserves_selected_top_or_bottom_datum(self):
        for datum in ('Top','Bottom'):
            state=SimpleNamespace(vars={'xy_origin':Value('old'),'z_origin':Value(datum)},status=Value(''))
            def set_single(group,filename,stock,name,layout):state.contours=group
            state.set_single_part=set_single
            state.add_part_object=lambda *args:self.fail('single part unexpectedly split')
            cam.App.accept_step_contours(state,[outer()],'example.step',1,cam.mat_identity(),3.,0,0)
            self.assertEqual(state.vars['z_origin'].get(),datum)
            self.assertEqual(state.vars['xy_origin'].get(),'선택점')


if __name__=='__main__':unittest.main()
