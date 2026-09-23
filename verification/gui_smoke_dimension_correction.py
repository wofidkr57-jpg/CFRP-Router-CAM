"""Portable settings and real App generation with size compensation; no CNC."""
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
        assert app.vars['inner_size_adjust'].get()==.10
        assert app.vars['outer_size_adjust'].get()==-.14
        tool=app.vars['tool_d'].get();wear=app.vars['tool_wear_loss_per_10m'].get()
        app.set_single_part([cam.Contour([(0,0),(20,0),(20,20),(0,20)],True)],'test.dxf')
        before=app.job_signature(app.config())
        app.vars['outer_size_adjust'].set(-.08)
        assert app.job_signature(app.config())!=before
        app.vars['inner_size_adjust'].set(.12)
        app.vars['show_toolpath'].set(True);app.redraw();app.update()
        assert app.collision_cache_key[-1]==(.12,-.08)
        with mock.patch.object(cam.messagebox,'askokcancel',return_value=True),mock.patch.object(cam.messagebox,'showerror') as errors:
            app.make_gcode()
        assert not errors.called,errors.call_args_list
        assert '(OUTER_SIZE_ADJUST_MM: -0.08)' in app.gcode
        app.vars['inner_size_adjust'].set(float('nan'))
        with mock.patch.object(cam.messagebox,'showerror') as errors:app.make_gcode()
        assert errors.called
        app.vars['inner_size_adjust'].set(.12);app.save_settings()
        assert app.vars['tool_d'].get()==tool and app.vars['tool_wear_loss_per_10m'].get()==wear
    finally:app.destroy()
    app=cam.App()
    try:
        assert app.vars['inner_size_adjust'].get()==.12 and app.vars['outer_size_adjust'].get()==-.08
        assert app.vars['tool_d'].get()==tool and app.vars['tool_wear_loss_per_10m'].get()==wear
    finally:app.destroy()
print('DIMENSION_CORRECTION_GUI_OK')
