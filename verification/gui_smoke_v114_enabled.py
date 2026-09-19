import os
import sys
import tempfile
from pathlib import Path
from types import SimpleNamespace
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import cfrp_router_cam as cam

with tempfile.TemporaryDirectory() as folder:
    os.environ['CFRP_CAM_LANGUAGE']='en'
    cam.App.executable_dir=lambda self:folder
    cam.App.appdata_settings_path=lambda self:str(Path(folder)/'fallback.json')
    app=cam.App();app.update()
    assert app.vars['safe_z_auto'].get()
    assert app.vars['approach_z'].get()==1
    assert app.vars['safe_z'].get()==2*app.vars['stock'].get()
    app.vars['stock'].set(2);assert app.vars['safe_z'].get()==4
    app.vars['safe_z_auto'].set(False);app.vars['safe_z'].set(10)
    app.vars['stock'].set(4);assert app.config()['safe_z']==10
    app.vars['safe_z_auto'].set(True);assert app.config()['safe_z']==8
    app.save_settings();app.vars['safe_z'].set(99);app.load_settings()
    assert app.vars['safe_z'].get()==8
    app.vars['stock'].set(3)

    contours=[cam.Contour([(x,0),(x+10,0),(x+10,10),(x,10)],forced_role='outer',layer=f'TEST_{i}') for i,x in enumerate((0,30,60))]
    app.set_single_part(contours,'synthetic',3);app.update()
    app.order_tree.selection_set(('c1','c2'));app.order_tree.focus('c1');app.tree_select();app.update()
    before=app.job_signature(app.config())
    bbox=app.order_tree.bbox('c1','enabled')
    result=app.tree_cell_click(SimpleNamespace(x=bbox[0]+5,y=bbox[1]+5,state=0))
    assert result=='break'
    app.update()
    assert set(app.order_tree.selection())=={'c1','c2'}
    editor=app.tree_role_editor
    editor.tk.call('ttk::combobox::Unpost',editor._w)
    editor.current(1);editor.event_generate('<<ComboboxSelected>>');app.update()
    assert [c.enabled for c in app.contours]==[True,False,False]
    assert not app.sel_enabled.get()
    assert app.order_tree.set('c1','enabled')==cam.ui_text('제외')
    assert 'disabled' in app.order_tree.item('c1','tags')
    assert app.job_signature(app.config())!=before
    code=cam.generate_gcode(app.contours,app.config())
    assert 'layer=TEST_0' in code and 'layer=TEST_1' not in code and 'layer=TEST_2' not in code
    assert not any(c.safety_excluded for c in app.contours)
    app.undo();app.update();assert all(c.enabled for c in app.contours)
    app.redo();app.update();assert [c.enabled for c in app.contours]==[True,False,False]
    app.order_tree.selection_set(('c1','c2'));app.tree_select()
    app.commit_tree_enabled_editor('c1','적용');app.update()
    assert all(c.enabled for c in app.contours)
    assert app.sel_enabled.get()
    # Single unselected row must not alter other rows.
    app.order_tree.selection_set('c0');app.tree_select()
    app.commit_tree_enabled_editor('c2','제외');app.update()
    assert [c.enabled for c in app.contours]==[True,True,False]
    app.destroy()
print('GUI_ENABLED_V114_OK')
