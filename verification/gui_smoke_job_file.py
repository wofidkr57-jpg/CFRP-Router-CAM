"""Portable job roundtrip, failed open/save, and cutting-distance consent."""
import os,sys,tempfile,json,copy
from pathlib import Path
from unittest import mock
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import cfrp_router_cam as cam
with tempfile.TemporaryDirectory() as tmp:
    os.environ['CFRP_CAM_LANGUAGE']='en'
    cam.App.executable_dir=lambda self:tmp
    cam.App.appdata_settings_path=lambda self:str(Path(tmp)/'settings.json')
    app=cam.App()
    try:
        app.example();app.vars['array_qty'].set(2);app.toggle_manual_array();app.toggle_manual_array()
        outer=[c for c in app.contours if c.role=='outer']
        outer[0].tabs=[10.0,20.0];outer[0].start_s=6.0;outer[0].outer_cut_order=2;outer[1].outer_cut_order=1
        outer[0].bridges=[((1.,2.),(3.,4.))]
        app.vars['feed'].set(555);app.vars['tool_wear_enabled'].set(False)
        app.start_text.insert('end','\n(TEST START)')
        app.onion_start_text.configure(state='normal');app.onion_start_text.insert('end','(FINISH START)')
        expected=app.job_snapshot();code=cam.generate_gcode(app.contours,app.config())
        path=str(Path(tmp)/'roundtrip.cfrpcam')
        with mock.patch.object(cam.filedialog,'asksaveasfilename',return_value=path):assert app.save_job()
        document=json.loads(Path(path).read_text(encoding='utf-8'))
        # The schema also restores projected pockets without the source STEP.
        pocket=cam.Contour([(0.,0.),(20.,0.),(20.,20.)],role='pocket',operation='pocket',pocket_holes=[[(1.,1.),(2.,1.),(2.,2.)]],pocket_max_depth=1.)
        assert cam.decode_job_value(json.loads(json.dumps(cam.asdict(pocket))),cam.Contour)==pocket
        app.update();app.destroy();app=cam.App();app.vars['feed'].set(999);app.gcode='STALE';app.gcode_signature='STALE'
        with mock.patch.object(cam.filedialog,'askopenfilename',return_value=path):assert app.open_job()
        assert json.loads(app.job_snapshot())==json.loads(expected), [(k,json.loads(expected)[k],json.loads(app.job_snapshot())[k]) for k in json.loads(expected) if json.loads(expected)[k]!=json.loads(app.job_snapshot())[k]]
        assert cam.parse_gcode_moves(cam.generate_gcode(app.contours,app.config()))==cam.parse_gcode_moves(code)
        assert not app.gcode and app.gcode_signature is None
        assert isinstance(app.contours[0].points[0],tuple)
        baseline=app.job_snapshot()
        for mutate in (lambda d:d.update(schema=999),lambda d:d['state']['contours'][0]['points'][0].__setitem__(0,float('nan')),lambda d:d['vars'].__setitem__('feed',-5)):
            bad=copy.deepcopy(document);mutate(bad);Path(path).write_text(json.dumps(bad),encoding='utf-8')
            with mock.patch.object(cam.filedialog,'askopenfilename',return_value=path),mock.patch.object(cam.messagebox,'showerror') as error:
                assert not app.open_job();assert error.called
            assert app.job_snapshot()==baseline
        old_bytes=Path(path).read_bytes()
        with mock.patch.object(cam.os,'replace',side_effect=OSError('test')),mock.patch.object(cam.messagebox,'showerror'):
            assert not app.save_job()
        assert Path(path).read_bytes()==old_bytes
        app.vars['feed'].set(556)
        with mock.patch.object(cam.messagebox,'askyesnocancel',return_value=None):assert not app.confirm_job_replace()
        # Consent gate exercised through the real generation handler, with only distance mocked.
        app.example();app.vars['tool_wear_enabled'].set(False)
        for accepted in (False,True):
            with mock.patch.object(cam,'machining_report',return_value=(18.043,35.)),mock.patch.object(cam.messagebox,'askyesno',return_value=accepted) as consent, mock.patch.object(cam.messagebox,'askokcancel',return_value=True),mock.patch.object(cam.messagebox,'showerror') as error:
                app.make_gcode()
                assert consent.called and consent.call_args.kwargs['default']=='no'
                assert bool(app.gcode)==accepted,(accepted,error.call_args_list)
                assert not error.called,error.call_args_list
                if accepted:assert "TOOL DISTANCE LIMIT OVERRIDE" in app.gcode
    finally:app.update();app.destroy()
print('JOB_FILE_GUI_OK')
