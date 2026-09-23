"""Exercise real click handlers and array duplication, with no machine I/O."""
import os,sys,tempfile
from pathlib import Path
from types import SimpleNamespace
from unittest import mock
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import cfrp_router_cam as cam

with tempfile.TemporaryDirectory() as tmp:
    os.environ['CFRP_CAM_LANGUAGE']='en'
    cam.App.executable_dir=lambda self:tmp
    cam.App.appdata_settings_path=lambda self:str(Path(tmp)/'fallback.json')
    app=cam.App()
    def click(x,y):
        app.view=(10,0,500)
        sx,sy=app.transform((x,y));app.canvas_click(SimpleNamespace(x=sx,y=sy,state=0))
    try:
        app.vars['feed'].set(777)
        for t,f in ((2,600),(3,550),(6,500)):
            app.vars['stock'].set(t);assert app.vars['feed'].get()==777
            app.apply_recommended_feed();assert app.vars['feed'].get()==f
            app.vars['feed'].set(777)
        app.vars['stock'].set(4);assert str(app.feed_recommend_btn.cget('state'))=='disabled'
        app.apply_recommended_feed();assert app.vars['feed'].get()==777
        app.vars['stock'].set(6);app.apply_recommended_feed()
        app.set_single_part([cam.Contour([(0,0),(40,0),(40,20),(0,20)],True)],'part.dxf')
        c=app.contours[0];c.tabs=[];c.tabs_enabled=True
        app.toggle_start();click(200,200);assert app.start_mode
        click(10,0);assert not app.start_mode and abs(c.start_s-10)<1e-6
        click(20,0);assert abs(c.start_s-10)<1e-6
        app.toggle_start();app.toggle_manual();assert not app.start_mode and app.manual_mode
        click(12,0);assert not app.manual_mode and len(c.tabs)==1
        click(22,0);assert len(c.tabs)==1
        app.toggle_manual();click(22,0);assert len(c.tabs)==2
        app.toggle_measure();click(0,0);assert app.measure_mode
        click(40,0);assert not app.measure_mode and app.measurement
        old=dict(app.measurement);click(20,0);assert app.measurement==old
        app.toggle_origin();click(0,0);assert not app.origin_mode
        app.vars['array_qty'].set(3);app.vars['sheet_w'].set(150);app.vars['sheet_h'].set(100)
        app.vars['array_dense'].set(False)
        with mock.patch.object(cam.messagebox,'showerror') as errors:app.auto_nest()
        assert not errors.called,errors.call_args_list
        assert len(app.contours)==3 and all(q.tabs==[12,22] for q in app.contours)
        app.manual_array_mode=True;app.toggle_start();assert not app.manual_array_mode
        app.toggle_start()
        app.contours=[cam.Contour([(0,0),(10,0)],False),cam.Contour([(10,1),(20,1)],False)]
        app.view_only=None;app.toggle_join();click(5,0);assert app.join_mode
        click(15,1);assert not app.join_mode and len(app.contours)==1
        app.save_settings()
    finally:app.destroy()
    app=cam.App()
    try:assert app.vars['stock'].get()==6 and app.vars['feed'].get()==500
    finally:app.destroy()
print('FEED_PICK_GUI_OK')
