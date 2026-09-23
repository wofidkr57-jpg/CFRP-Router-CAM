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
    try:
        app.example();app.vars['array_qty'].set(2);app.toggle_manual_array();app.toggle_manual_array();app.update()
        outer=[c for c in app.contours if c.role=='outer'];first=outer[-1]
        idx=next(i for i,c in enumerate(app.contours) if c is first);iid=f'c{idx}'
        app.order_tree.see(iid);app.update()
        box=app.order_tree.bbox(iid,'manual');assert box
        app.tree_cell_click(SimpleNamespace(x=box[0]+box[2]//2,y=box[1]+box[3]//2,state=0));app.update()
        editor=app.tree_role_editor;assert editor.winfo_exists()
        signature=app.job_signature(app.config())
        editor.delete(0,'end');editor.insert(0,'1');editor.event_generate('<Return>');app.update()
        assert first.outer_cut_order==1 and app.job_signature(app.config())!=signature
        ordered=cam.ordered_contours(app.contours)
        assert [c for c in ordered if c.role=='outer'][0] is first
        assert all(c.role=='inner' for c in ordered[:4])
        assert '#2' in app.order_tree.set(iid,'part')
        app.undo();assert all(c.outer_cut_order is None for c in app.contours)
        app.redo();first=next(c for c in app.contours if c.outer_cut_order==1)
        app.set_outer_order(first,'0');assert first.outer_cut_order==1
        app.set_outer_order(first,'');assert first.outer_cut_order is None
        app.refresh_order_tree();app.update()
        panel=app.order_tree.master.master;panel.sashpos(0,140);panel.sashpos(1,480);app.update()
        outers=[c for c in cam.ordered_contours(app.contours) if c.role=='outer']
        def row(c):return 'c'+str(next(i for i,q in enumerate(app.contours) if q is c))
        app.order_tree.see(row(outers[0]));app.update()
        a=app.order_tree.bbox(row(outers[0]),'seq');b=app.order_tree.bbox(row(outers[1]),'seq')
        assert a and b
        app.tree_cell_click(SimpleNamespace(x=a[0]+a[2]//2,y=a[1]+a[3]//2,state=0))
        event=SimpleNamespace(x=b[0]+b[2]//2,y=b[1]+b[3]//2,state=0)
        app.drag_outer_order(event);app.update()
        assert app.order_insert_line.winfo_ismapped()
        assert abs(app.order_insert_line.winfo_y()-(b[1]+b[3]-1))<=1
        app.drop_outer_order(event);app.update()
        assert not app.order_insert_line.winfo_ismapped()
        assert [c for c in cam.ordered_contours(app.contours) if c.role=='outer']==list(reversed(outers))
        assert all(c.role=='inner' for c in cam.ordered_contours(app.contours)[:4])
        assert [c.outer_cut_order for c in outers]==[2,1]
        app.undo();assert all(c.outer_cut_order is None for c in app.contours)
        app.redo();app.reset_outer_order();assert all(c.outer_cut_order is None for c in app.contours)
        # Upper half means BEFORE, regardless of drag direction.
        outers=[c for c in cam.ordered_contours(app.contours) if c.role=="outer"]
        app.refresh_order_tree();app.update()
        a=app.order_tree.bbox(row(outers[1]),'seq');b=app.order_tree.bbox(row(outers[0]),'seq')
        app.tree_cell_click(SimpleNamespace(x=a[0]+10,y=a[1]+a[3]//2,state=0))
        event=SimpleNamespace(x=b[0]+10,y=b[1]+2,state=0)
        app.drag_outer_order(event);app.update()
        assert abs(app.order_insert_line.winfo_y()-(b[1]-1))<=1
        app.drop_outer_order(event);app.update()
        assert [c for c in cam.ordered_contours(app.contours) if c.role=='outer']==list(reversed(outers))
        app.move_outer_step(1);assert [c for c in cam.ordered_contours(app.contours) if c.role=='outer']==outers
        app.move_outer_step(1);assert [c for c in cam.ordered_contours(app.contours) if c.role=='outer']==outers
        # Dropping outside the list must not apply a stale insertion target.
        app.order_drag=(outers[0],0,(outers[1],True))
        ranks=[c.outer_cut_order for c in outers]
        app.drop_outer_order(SimpleNamespace(x=-20,y=60));assert [c.outer_cut_order for c in outers]==ranks
        assert app.order_scroll_after is None
        print('OUTER_ORDER_GUI_OK')
    finally:app.destroy()
