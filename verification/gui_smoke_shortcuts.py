"""Real Tk shortcut events, one-shot picking and focus isolation; no machine I/O."""
import os,sys,tempfile
from pathlib import Path
from types import SimpleNamespace
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import cfrp_router_cam as cam

with tempfile.TemporaryDirectory() as tmp:
    os.environ['CFRP_CAM_LANGUAGE']='en'
    cam.App.executable_dir=lambda self:tmp
    cam.App.appdata_settings_path=lambda self:str(Path(tmp)/'fallback.json')
    app=cam.App()
    def key(name,state=0,widget=None):
        w=widget if widget is not None else app.canvas
        w.focus_force();app.update();w.event_generate('<KeyPress>',keysym=name,state=state);app.update()
    def click(x,y):
        sx,sy=app.transform((x,y));app.canvas_click(SimpleNamespace(x=sx,y=sy,state=0));app.update()
    try:
        app.set_single_part([cam.Contour([(0,0),(40,0),(40,20),(0,20)],True)],'part.dxf')
        app.fit_view();app.update();c=app.contours[0];c.tabs=[];c.tabs_enabled=True
        key('t',8);assert app.manual_mode
        key('t',8);assert app.manual_mode  # OS repeat must not toggle off.
        click(12,0);assert not app.manual_mode and len(c.tabs)==1
        click(22,0);assert len(c.tabs)==1
        key('T',1);click(22,0);assert not app.manual_mode and len(c.tabs)==2
        key('s');assert app.start_mode and not app.manual_mode
        click(10,0);assert not app.start_mode and abs(c.start_s-10)<0.1
        key('S',1);assert app.start_mode
        key('t');assert app.manual_mode and not app.start_mode
        key('Escape');assert not any((app.manual_mode,app.start_mode,app.measure_mode,app.origin_mode,app.join_mode))
        for state in (4,0x20000):
            key('t',state);assert not app.manual_mode
        entry=cam.ttk.Entry(app);entry.place(x=100,y=100,width=150,height=30);app.update()
        key('t',widget=entry);key('s',widget=entry)
        assert entry.get()=='ts' and not app.manual_mode and not app.start_mode, (entry.get(),app.manual_mode,app.start_mode)
        dialog=cam.tk.Toplevel(app);other=cam.tk.Canvas(dialog);other.pack();app.update()
        key('t',widget=other);assert not app.manual_mode
        dialog.destroy();entry.destroy()
        app.manual_array_mode=True;key('s');assert app.start_mode and not app.manual_array_mode
        key('Escape');app.toggle_measure();app.measure_start=(0,0)
        key('Escape');assert not app.measure_mode and app.measure_start is None
        app.view=(1,999,999);key('Home');assert app.view!=(1,999,999)
        assert 'Ctrl+C/V' in app.shortcut_help.cget('text')
        host=app.settings_canvas.master;host.master.select(host);app.update()
        app.settings_canvas.yview_moveto(1);app.update()
        help_label=app.shortcut_help
        assert help_label.winfo_height()==help_label.winfo_reqheight()
        assert help_label.winfo_rooty()>=app.settings_canvas.winfo_rooty()
        assert help_label.winfo_rooty()+help_label.winfo_height()<=app.settings_canvas.winfo_rooty()+app.settings_canvas.winfo_height()
    finally:app.destroy()
print('SHORTCUT_GUI_OK')
