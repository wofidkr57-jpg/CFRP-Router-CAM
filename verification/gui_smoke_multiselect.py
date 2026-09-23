"""Ctrl-click whole instances and group dragging on the real canvas."""
import os,sys,tempfile,copy
from pathlib import Path
from types import SimpleNamespace
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import cfrp_router_cam as cam

with tempfile.TemporaryDirectory() as tmp:
    os.environ['CFRP_CAM_LANGUAGE']='en'
    cam.App.executable_dir=lambda self:tmp
    cam.App.appdata_settings_path=lambda self:str(Path(tmp)/'fallback.json')
    app=cam.App()
    try:
        app.example();app.vars['array_qty'].set(3);app.vars['sheet_w'].set(400)
        app.toggle_manual_array();app.update()
        keys=sorted(cam.contour_group_bounds_map(app.contours))
        def event(key,state=0):
            b=cam.contour_group_bounds(app.contours,key)
            x,y=app.transform(((b[0]+b[2])/2,(b[1]+b[3])/2))
            return SimpleNamespace(x=x,y=y,state=state,widget=app.canvas)
        def click(key,ctrl=False):
            e=event(key,4 if ctrl else 0);app.canvas_press(e);app.canvas_left_release(e)
        click(keys[0]);click(keys[1],True)
        assert app.selected_instance_keys()==set(keys[:2]) and len(app.selected_contours)==6
        click(keys[1],True);assert app.selected_instance_keys()=={keys[0]}
        click(keys[1],True)
        before=copy.deepcopy(app.contours)
        e=event(keys[0]);app.canvas_press(e)
        scale=app.view[0];end=SimpleNamespace(x=e.x+scale*.3,y=e.y-scale*.2,state=0)
        app.canvas_left_drag(end);app.canvas_left_release(end)
        for c,old in zip(app.contours,before):
            dx,dy=(.3,.2) if cam.contour_group_key(c) in keys[:2] else (0,0)
            assert all(abs(x-ox-dx)<1e-7 and abs(y-oy-dy)<1e-7 for (x,y),(ox,oy) in zip(c.points,old.points))
        app.undo();assert app.contours==before
        click(keys[0]);click(keys[1],True)
        app.nudge_selected_instances(SimpleNamespace(widget=app.canvas,state=0,keysym='Right'))
        app.copy_selected_instances();assert len(app.instance_clipboard)==6
        app.delete_selected_instances();assert len(app.contours)==3
        app.undo();assert len(app.contours)==9
        click(keys[2]);assert app.selected_instance_keys()=={keys[2]}
        empty=SimpleNamespace(x=-100,y=-100,state=0)
        app.canvas_press(empty);app.canvas_left_release(empty);assert not app.selected_instance_keys()
        print('MULTISELECT_GUI_OK')
    finally:app.destroy()
