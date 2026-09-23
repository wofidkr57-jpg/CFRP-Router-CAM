import os,sys,tempfile
from pathlib import Path
from unittest import mock
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import cfrp_router_cam as cam

with tempfile.TemporaryDirectory() as tmp:
    os.environ['CFRP_CAM_LANGUAGE']='en'
    cam.App.executable_dir=lambda self:tmp
    cam.App.appdata_settings_path=lambda self:str(Path(tmp)/'fallback.json')
    app=cam.App()
    try:
        app.example();app.vars['array_qty'].set(1);app.toggle_manual_array();app.update()
        key=next(iter(cam.contour_group_bounds_map(app.contours)));app.view=(10,0,500)
        b=cam.contour_group_bounds(app.contours,key);edge=app.vars['array_edge'].get()
        dx,dy,hit=app.snap_manual_move({key},edge-b[0]+.3,5)
        assert hit and abs(b[0]+dx-edge)<1e-8
        for _ in range(2):
            dx,dy,hit=app.snap_manual_move({key},.3,5);assert not hit and dx==.3
        assert app.snap_manual_move({key},edge-b[0]+.3,5)[2]
        app.snap_cooldown={}
        sw,sh=app.sheet_size
        dx,dy,hit=app.snap_manual_move({key},sw-edge-b[2]-.2,sh-edge-b[3]-.2)
        assert hit and abs(b[2]+dx-(sw-edge))<1e-8 and abs(b[3]+dy-(sh-edge))<1e-8
        app.snap_cooldown={}
        dx,dy,hit=app.snap_manual_move({key},10,10);assert not hit and (dx,dy)==(10,10)
        app.vars['inner_size_adjust'].set(0);app.vars['outer_size_adjust'].set(0)
        with mock.patch.object(cam,'tool_sweep_collisions',side_effect=AssertionError('heavy collision')):
            app.redraw()
        items=app.canvas.find_withtag('manual_offset');assert len(items)==3
        old=app.canvas.coords(items[0])
        app.vars['tool_d'].set(4);app.redraw()
        assert app.canvas.coords(app.canvas.find_withtag('manual_offset')[0])!=old
        app.vars['show_toolpath'].set(False);app.redraw();assert not app.canvas.find_withtag('manual_offset')
        print('SNAP_PREVIEW_GUI_OK')
    finally:app.destroy()
