"""Real Tk order selection, preview/NC consistency, persistence and old jobs."""
import copy,json,os,re,sys,tempfile
from pathlib import Path
from unittest import mock
sys.path[:0]=[str(Path(__file__).resolve().parents[1]),str(Path(__file__).resolve().parent)]
import cfrp_router_cam as cam
from test_center_out_order import array

with tempfile.TemporaryDirectory() as tmp:
    os.environ['CFRP_CAM_LANGUAGE']='en'
    cam.App.executable_dir=lambda self:tmp
    cam.App.appdata_settings_path=lambda self:str(Path(tmp)/'fallback.json')
    app=cam.App()
    try:
        app.update();cs=array()
        for c in cs:c.points=[(x+40,y+40) for x,y in c.points]
        app.contours=cs;app.part_objects=[cam.PartObject(1,'Synthetic array',copy.deepcopy(cs))]
        app.next_object_id=2;app.nest_active=True;app.sheet_size=(80.,80.)
        app.vars['sheet_w'].set(80);app.vars['sheet_h'].set(80)
        app.vars['tool_wear_enabled'].set(False);app.vars['tab_count'].set(0)
        app.view_initialized=False;app.redraw();app.update()
        assert tuple(app.outer_order_combo.cget('values'))==('Nearest first','Center outward (CW)','Center outward (CCW)')
        old=app.config();sig=app.job_signature(old)
        results={}
        for mode,choice in (('center_cw',1),('center_ccw',2)):
            app.outer_order_combo.current(choice);app.outer_order_combo.event_generate('<<ComboboxSelected>>');app.update()
            cfg=app.config();assert cam.outer_order_mode(cfg['outer_order_mode'])==mode
            seq=cam.ordered_contours(app.contours,True,outer_order=mode)
            shown=[app.contours[int(i[1:])].layer for i in app.order_tree.get_children()]
            assert shown==[c.layer for c in seq]
            assert [c.layer for c in app.preview_order_cache]==shown
            assert app.job_signature(cfg)!=sig
            with mock.patch.object(cam.messagebox,'askokcancel',return_value=True),mock.patch.object(cam.messagebox,'showerror') as error:
                app.make_gcode();assert not error.called,error.call_args_list
            assert re.findall(r'\(Contour \d+: .*?layer=([^,]+)',app.gcode)==shown
            assert cam.parse_gcode_moves(app.gcode)
            results[mode]=shown
        assert results['center_cw']!=results['center_ccw']
        # Explicit ranks take priority, and Auto outer order restores the selected mode.
        app.contours[0].outer_cut_order=1;app.redraw();app.update()
        assert app.order_tree.get_children()[0]=='c0'
        app.reset_outer_order();app.update()
        assert app.order_tree.get_children()[0]=='c4'
        app.undo();assert app.contours[0].outer_cut_order==1
        app.redo();assert all(c.outer_cut_order is None for c in app.contours)
        # Settings and job files preserve the choice, including opposite-language enums.
        app.save_settings();doc=json.loads(json.dumps(app.job_document()));path=Path(tmp)/'roundtrip.cfrpcam'
        path.write_text(json.dumps(doc),encoding='utf-8')
        app.destroy();app=cam.App();app.update()
        assert cam.outer_order_mode(app.vars['outer_order_mode'].get())=='center_ccw'
        with mock.patch.object(cam.filedialog,'askopenfilename',return_value=str(path)):assert app.open_job()
        assert cam.outer_order_mode(app.config()['outer_order_mode'])=='center_ccw'
        old_doc=copy.deepcopy(doc);old_doc['vars'].pop('outer_order_mode');old_doc['app_version']='1.36'
        app.decode_job(old_doc);app.apply_job_values(old_doc)
        assert cam.outer_order_mode(app.vars['outer_order_mode'].get())=='nearest'
        bad=copy.deepcopy(doc);bad['vars']['outer_order_mode']='broken'
        try:app.decode_job(bad)
        except ValueError:pass
        else:raise AssertionError('invalid mode accepted')
        app.vars['outer_order_mode'].set('중앙 → 바깥 (시계)');app.save_settings();app.destroy()
        os.environ['CFRP_CAM_LANGUAGE']='ko';app=cam.App();app.update()
        assert cam.outer_order_mode(app.vars['outer_order_mode'].get())=='center_cw'
        assert app.vars['outer_order_mode'].get()=='중앙 → 바깥 (시계)'
        print('CENTER_OUT_ORDER_GUI_OK',json.dumps(results))
    finally:app.destroy()
