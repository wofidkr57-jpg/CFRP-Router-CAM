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
        app.vars['inner_size_adjust'].set(0);app.vars['outer_size_adjust'].set(0)
        # Fit the actual viewport, including the 1024px desktop on Windows CI.
        app.view_initialized=False
        with mock.patch.object(cam,'tool_sweep_collisions',side_effect=AssertionError('heavy collision')):
            app.redraw()
        items=app.canvas.find_withtag('manual_offset');assert len(items)==3
        old=app.canvas.coords(items[0])
        app.vars['tool_d'].set(4);app.redraw()
        assert app.canvas.coords(app.canvas.find_withtag('manual_offset')[0])!=old
        app.vars['show_toolpath'].set(False);app.redraw();assert not app.canvas.find_withtag('manual_offset')
        print('PLACEMENT_PREVIEW_GUI_OK')
    finally:app.destroy()
