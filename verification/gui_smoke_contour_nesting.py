"""Real Tk part offsets, nesting, undo and mode persistence; no machine access."""
import os
import sys
import tempfile
from pathlib import Path
from unittest import mock
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import cfrp_router_cam as cam
from test_contour_nesting import placed_shape

with tempfile.TemporaryDirectory() as tmp:
    os.environ['CFRP_CAM_LANGUAGE']='en'
    cam.App.executable_dir=lambda self:tmp
    cam.App.appdata_settings_path=lambda self:str(Path(tmp)/'fallback.json')
    app=cam.App()
    try:
        app.set_single_part([cam.Contour([(0,0),(40,0),(0,20)],True)],'triangle.dxf')
        app.object_tree.selection_set('o1');app.object_tree_select()
        app.object_offset.set('0.5');app.apply_object_offset()
        assert app.part_objects[0].nest_offset==.5
        app.object_offset.set('nan')
        with mock.patch.object(cam.messagebox,'showerror') as errors:app.apply_object_offset()
        assert errors.called and app.part_objects[0].nest_offset==.5
        app.object_qty.set(2);app.apply_object_quantity()
        app.vars['array_dense'].set(True);app.vars['sheet_w'].set(45);app.vars['sheet_h'].set(30)
        app.vars['array_edge'].set(0);app.vars['array_rotate'].set(False)
        with mock.patch.object(cam.messagebox,'askokcancel',return_value=True) as warning,mock.patch.object(cam.messagebox,'showerror') as errors:
            app.auto_nest()
        assert warning.called and not errors.called,errors.call_args_list
        assert app.nest_active and len(app.contours)==2
        from shapely.geometry import Polygon
        a,b=[Polygon(c.points) for c in app.contours]
        assert a.distance(b)>=1-1e-6 and a.intersection(b).area<1e-7
        assert app.part_objects[0].nest_offset==.5
        app.undo();assert not app.nest_active and app.part_objects[0].nest_offset==.5
        with mock.patch.object(cam.messagebox,'askokcancel',return_value=False):app.auto_nest()
        assert not app.nest_active
        app.object_tree.selection_set('o1');app.object_tree_select()
        app.object_offset.set('');app.apply_object_offset()
        assert app.part_objects[0].nest_offset is None
        app.vars['array_dense'].set(False)
        with mock.patch.object(cam.messagebox,'showwarning'),mock.patch.object(cam.messagebox,'showerror') as errors:app.auto_nest()
        assert not errors.called and len(app.contours)==1
        app.vars['array_dense'].set(True);app.save_settings()
    finally:app.destroy()
    app=cam.App()
    try:assert app.vars['array_dense'].get()
    finally:app.destroy()
print('Contour nesting GUI smoke passed')
