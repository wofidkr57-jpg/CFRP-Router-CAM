"""Settings persistence, legacy jobs, and balanced generation through the real UI."""
import copy,json,os,sys,tempfile
from pathlib import Path
from unittest import mock
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import cfrp_router_cam as cam
with tempfile.TemporaryDirectory() as tmp:
    os.environ['CFRP_CAM_LANGUAGE']='ko'
    cam.App.executable_dir=lambda self:tmp
    cam.App.appdata_settings_path=lambda self:str(Path(tmp)/'settings.json')
    app=cam.App()
    try:
        app.example();old=copy.deepcopy(app.job_document())
        for key in list(old['vars']):
            if key.startswith('tool_change_'):del old['vars'][key]
        values=dict(tool_change_enabled=True,tool_change_limit_m=8.,tool_change_macro='M881',
                    tool_change_return_z=-70.,tool_change_dwell=3.,z_origin='Bottom',
                    wall_finish=False,onion_skin_enabled=False,onion_split=False,
                    full_depth=True,lead=0.,tool_wear_enabled=False,m8_enabled=True)
        for key,value in values.items():app.vars[key].set(value)
        app.contours=[cam.Contour([(0.,i*10.),(1000.,i*10.)],closed=False) for i in range(18)]
        with mock.patch.object(cam.messagebox,'askyesno') as consent, mock.patch.object(cam.messagebox,'askokcancel',return_value=True) as confirm, mock.patch.object(cam.messagebox,'showerror') as error:
            app.make_gcode()
            assert not error.called,error.call_args_list
            assert not consent.called,consent.call_args_list
            assert confirm.called
            assert app.gcode.count('\nM881\n')==2
            assert '(BALANCED TOOL LOADS M: 6, 6, 6)' in app.gcode
        app.save_settings();snapshot=app.job_document()
        app.update();app.destroy();app=cam.App()
        assert all(app.vars[k].get()==v for k,v in values.items())
        decoded=app.decode_job(json.loads(json.dumps(snapshot)))
        assert decoded is not None
        # Opening old jobs must not inherit an enabled replacement mode.
        path=Path(tmp)/'legacy.cfrpcam';path.write_text(json.dumps(old),encoding='utf-8')
        with mock.patch.object(cam.filedialog,'askopenfilename',return_value=str(path)),mock.patch.object(cam.messagebox,'askyesnocancel',return_value=False):
            assert app.open_job()
        assert app.vars['tool_change_enabled'].get() is False
        assert app.vars['tool_change_macro'].get()=='M881'
        assert app.vars['tool_change_return_z'].get()==-70.
        app.update()
    finally:app.destroy()
print('TOOL_REPLACEMENT_GUI_OK')
