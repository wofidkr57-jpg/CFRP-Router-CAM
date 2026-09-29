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
            seq=cam.ordered_contours(app.contours,True,outer_order=mode,sheet_center=cam.sheet_center_from_config(cfg))
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
        # Keep the parts unchanged but enlarge the sheet: center moves from (40,40) to (120,120).
        # This must update the actual Entry -> tree -> cached preview -> cached NC path.
        before_points=[list(c.points) for c in app.contours]
        before_order=[c.layer for c in app.preview_order_cache]
        before_key=app.preview_order_cache_key;before_sig=app.gcode_signature
        for key in ('sheet_w','sheet_h'):
            entry=app.sheet_entries[key];entry.delete(0,'end');entry.insert(0,'240')
            entry.event_generate('<FocusOut>');app.update()
        cfg=app.config();assert cam.sheet_center_from_config(cfg)==(120.,120.)
        assert app.sheet_size==(240.,240.)
        assert [list(c.points) for c in app.contours]==before_points
        shown=[app.contours[int(i[1:])].layer for i in app.order_tree.get_children()]
        expected=[c.layer for c in cam.ordered_contours(app.contours,True,outer_order='center_ccw',sheet_center=(120.,120.))]
        assert shown==expected and shown!=before_order
        assert [c.layer for c in app.preview_order_cache]==shown and app.preview_order_cache_key!=before_key
        assert app.job_signature(cfg)!=before_sig
        with mock.patch.object(cam.messagebox,'askokcancel',return_value=True),mock.patch.object(cam.messagebox,'showerror') as error:
            app.make_gcode();assert not error.called,error.call_args_list
        assert re.findall(r'\(Contour \d+: .*?layer=([^,]+)',app.gcode)==shown
        assert '(OUTER_ORDER_CENTER_SOURCE_X_MM: 120)' in app.gcode
        # Incomplete/invalid sheet input must not crash a redraw or produce NC.
        entry=app.sheet_entries['sheet_w'];entry.delete(0,'end');app.redraw();app.update()
        try:app.config()
        except (ValueError,cam.tk.TclError):pass
        else:raise AssertionError('empty sheet accepted')
        entry.insert(0,'240');entry.event_generate('<FocusOut>');app.update()
        # Settings and job files preserve the choice and sheet dimensions, including opposite-language enums.
        app.save_settings();doc=json.loads(json.dumps(app.job_document()));path=Path(tmp)/'roundtrip.cfrpcam'
        path.write_text(json.dumps(doc),encoding='utf-8')
        app.destroy();app=cam.App();app.update()
        assert cam.outer_order_mode(app.vars['outer_order_mode'].get())=='center_ccw'
        with mock.patch.object(cam.filedialog,'askopenfilename',return_value=str(path)):assert app.open_job()
        assert cam.outer_order_mode(app.config()['outer_order_mode'])=='center_ccw'
        assert cam.sheet_center_from_config(app.config())==(120.,120.)
        assert [c.layer for c in app.preview_order_cache]==shown
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
