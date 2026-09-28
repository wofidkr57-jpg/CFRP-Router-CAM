"""Exercise real Tk controls, persistence, generation and paired save; no CNC."""
import os
import sys
import tempfile
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
        # A disabled feature may retain values from a thicker previous job.
        app.vars['stock'].set(2);app.vars['onion_skin'].set(6)
        app.vars['onion_skin_enabled'].set(False);app.vars['onion_split'].set(False)
        assert app.config()['onion_skin']==6
        app.contours=[cam.Contour([(0,0),(40,0),(40,30),(0,30)],closed=True,role='outer')]
        with mock.patch.object(cam.messagebox,'showerror') as errors:
            app.make_gcode();assert not errors.called,errors.call_args_list
        assert app.gcode and '(ONION_SKIN: NO)' in app.gcode
        app.vars['onion_skin_enabled'].set(True)
        try:app.config()
        except ValueError as exc:assert '판 두께 미만' in str(exc)
        else:raise AssertionError('Enabled onion skin must reject remaining >= stock')
        app.vars['onion_skin_enabled'].set(False);app.vars['finish_allowance'].set(-.1)
        try:app.config()
        except ValueError as exc:assert '황삭 측면 여유' in str(exc) and '어니언스킨' not in str(exc)
        else:raise AssertionError('Roughing allowance validation must remain independent')
        app.vars['finish_allowance'].set(.12);app.vars['onion_skin'].set(.2)
        assert str(app.onion_start_text.cget('state'))=='disabled'
        app.vars['onion_split'].set(True);app.sync_onion_split()
        assert str(app.onion_start_text.cget('state'))=='normal'
        app.vars['stock'].set(6);app.vars['tool_d'].set(2)
        app.vars['lead'].set(0);app.vars['tool_wear_enabled'].set(False)
        app.start_text.delete('1.0','end');app.start_text.insert('1.0','G21\nG90\nG54\nM0 (COMMON START)\nS{RPM} M3')
        app.onion_start_text.insert('1.0','G21\nG90\nG54\nM0 (FINISH START)\nS{RPM} M3')
        app.onion_end_text.insert('1.0','G0 Z{SAFE_Z}\nM5\nM2 (FINISH END)')
        app.contours=[cam.Contour([(0,0),(40,0),(40,30),(0,30)],closed=True,role='outer')]
        app.filename='example.dxf'
        with mock.patch.object(cam.messagebox,'askokcancel',return_value=True),mock.patch.object(cam.messagebox,'showerror') as errors:
            app.make_gcode()
            assert not errors.called,errors.call_args_list
        assert [label for label,_ in app.gcode_parts]==['ROUGH','FINISH']
        rough,finish=[code for _,code in app.gcode_parts]
        assert 'COMMON START' in rough and 'FINISH START' not in rough
        assert 'FINISH START' in finish and 'COMMON START' not in finish
        assert 'FINISH END' in finish and 'FINISH END' not in rough
        signature=app.gcode_signature
        app.onion_end_text.insert('end','\n(COMMENT CHANGE)')
        assert app.job_signature(app.config())!=signature
        with mock.patch.object(cam.messagebox,'askokcancel',return_value=True),mock.patch.object(cam.messagebox,'showinfo'),mock.patch.object(cam.messagebox,'showerror') as errors,mock.patch.object(cam.filedialog,'asksaveasfilename',return_value=str(Path(tmp)/'job.nc')):
            app.save_gcode()
            assert not errors.called,errors.call_args_list
        files=list(Path(tmp).glob('*.nc'))
        assert len(files)==2 and any(p.stem.endswith('_ROUGH') for p in files) and any(p.stem.endswith('_FINISH') for p in files)
        app.vars['onion_split'].set(False);app.sync_onion_split();app.save_settings()
    finally:app.destroy()
    app=cam.App()
    try:
        assert not app.vars['onion_split'].get()
        assert 'FINISH START' in app.onion_start_text.get('1.0','end')
        assert 'FINISH END' in app.onion_end_text.get('1.0','end')
        app.vars['onion_split'].set(True);app.sync_onion_split()
        app.onion_start_text.delete('1.0','end');app.onion_end_text.delete('1.0','end')
        cfg=app.config()
        c=cam.Contour([(0,0),(40,0),(40,30),(0,30)],closed=True,role='outer')
        jobs=cam.machining_jobs([c],cfg)
        assert jobs[0][1]['start_code']==jobs[1][1]['start_code']
        assert jobs[0][1]['end_code']==jobs[1][1]['end_code']
    finally:app.destroy()
print('GUI_ONION_SPLIT_OK generation, overrides, save, restart, blank fallback')
