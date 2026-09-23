"""Quantity preview and canvas-only instance deletion; no machine I/O."""
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
    try:
        app.example();app.update()
        oid=app.part_objects[0].object_id
        app.object_tree.selection_set(f'o{oid}');app.update()
        app.contours[0].tabs=[10,20]
        original=[list(c.points) for c in app.contours]
        app.vars['array_dense'].set(True)  # Quantity must never launch dense search.
        def apply(q):
            app.object_qty.set(q);app.apply_object_quantity()
        def count():return len(cam.contour_group_bounds_map(app.contours))
        with mock.patch.object(cam,'best_contour_nesting',side_effect=AssertionError('dense search')):
            apply(4)
        assert count()==4 and len(app.contours)==12
        assert [c.points for c in app.contours[:3]]==original
        assert [c.tabs for c in app.contours[::3]]==[[10,20]]*4
        before=[list(c.points) for c in app.contours]
        apply(4);assert [c.points for c in app.contours]==before
        apply(2);assert count()==2
        app.undo();assert count()==4
        # Selecting an inner contour deletes its whole instance, not the other copies.
        target=app.contours[4];key=cam.contour_group_key(target)
        app.set_contour_selection([target],target)
        app.delete_selected_instances(SimpleNamespace(widget=app.object_qty_spin))
        assert count()==4
        app.update();app.canvas.focus_force();app.update()
        app.canvas.event_generate('<Delete>');app.update()
        assert count()==3 and key not in cam.contour_group_bounds_map(app.contours)
        assert app.part_objects[0].quantity==3
        app.undo();assert count()==4 and app.part_objects[0].quantity==4
        app.redo();assert count()==3
        apply(5);assert count()==5  # Non-contiguous instance IDs remain unique.
        apply(0);assert not app.contours
        apply(2);assert count()==2 and len(app.contours)==6
        assert app.contours[0].tabs==[10,20]
        app.manual_array_mode=True
        app.manual_array_selected=cam.contour_group_key(app.contours[0])
        app.delete_selected_instances();assert count()==1
        app.vars['sheet_w'].set(10);app.vars['sheet_h'].set(10)
        apply(3);assert count()==3 and 'Outside sheet: 3' in app.status.get()
        with mock.patch.object(cam.messagebox,'showerror') as error:
            apply(-1);assert count()==3 and error.called
        app.manual_array_mode=False
        selected=app.contours[:6]
        app.set_contour_selection(selected,selected[0])
        app.update();app.canvas.focus_force();app.update()
        app.canvas.event_generate('<Control-c>');app.update()
        saved=[list(c.points) for c in app.instance_clipboard]
        app.canvas.event_generate('<Control-v>');app.update()
        assert count()==5 and len(app.selected_contours)==6
        pasted=app.contours[-6:]
        dx=pasted[0].points[0][0]-saved[0][0][0];dy=pasted[0].points[0][1]-saved[0][0][1]
        for c,points in zip(pasted,saved):
            assert all(abs(x-px-dx)<1e-8 and abs(y-py-dy)<1e-8 for (x,y),(px,py) in zip(c.points,points))
        assert pasted[0].tabs==[10,20]
        app.undo();assert count()==3
        app.redo();assert count()==5
        app.paste_selected_instances(SimpleNamespace(widget=app.object_qty_spin));assert count()==5
        app.example();app.paste_selected_instances();assert count()==1
        app.manual_array_mode=False
        app.contours[0].tabs=[10,20];app.contours[0].start_s=7
        app.set_contour_selection([app.contours[1]],app.contours[1])
        before=[list(c.points) for c in app.contours]
        app.update();app.canvas.focus_force();app.update()
        app.canvas.event_generate('<Right>');app.update()
        for c,points in zip(app.contours,before):
            assert all(abs(x-px-1)<1e-8 and abs(y-py)<1e-8 for (x,y),(px,py) in zip(c.points,points))
        assert app.contours[0].tabs==[10,20] and app.contours[0].start_s==7
        app.canvas.event_generate('<Shift-Up>');app.update()
        assert abs(app.contours[0].points[0][1]-before[0][0][1]-.1)<1e-8
        app.undo();app.undo();assert [c.points for c in app.contours]==before
        app.redo();assert abs(app.contours[0].points[0][0]-before[0][0][0]-1)<1e-8
        app.manual_array_mode=True;app.manual_array_selected=cam.contour_group_key(app.contours[0])
        app.canvas.event_generate('<Left>');app.update()
        app.canvas.event_generate('<Down>');app.update()
        assert abs(app.contours[0].points[0][0]-before[0][0][0])<1e-8
        assert abs(app.contours[0].points[0][1]-before[0][0][1]+1)<1e-8
        before=[list(c.points) for c in app.contours]
        app.nudge_selected_instances(SimpleNamespace(widget=app.object_qty_spin,state=0,keysym='Right'))
        app.start_mode=True;app.canvas.event_generate('<Right>');app.update();app.start_mode=False
        app.canvas.event_generate('<Control-Right>');app.update()
        assert [c.points for c in app.contours]==before
        # Windows hold delivers repeated KeyPress events; every repeat must move.
        for _ in range(5):app.canvas.event_generate('<Right>');app.update()
        assert abs(app.contours[0].points[0][0]-before[0][0][0]-5)<1e-8
        before=[list(c.points) for c in app.contours]
        b=cam.contour_group_bounds(app.contours,app.manual_array_selected)
        if app.tk.call('tk','windowingsystem')=='win32':
            # Actual Windows arrows include Extended; Num Lock adds Mod1.
            for state,step in ((0x40008,1),(0x40009,.1),(0x4000a,1)):
                x=app.contours[0].points[0][0]
                app.canvas.event_generate('<KeyPress-Right>',state=state);app.update()
                assert abs(app.contours[0].points[0][0]-x-step)<1e-8
                app.undo()
            app.manual_array_selected=cam.contour_group_key(app.contours[0])
            app.canvas.event_generate('<KeyPress-Right>',state=0x60008);app.update()
            assert [c.points for c in app.contours]==before
        app.canvas.event_generate('<f>');app.update()
        for c,points in zip(app.contours,before):
            assert all(abs(x-(b[0]+b[2]-px))<1e-8 and abs(y-py)<1e-8 for (x,y),(px,py) in zip(c.points,points))
        assert app.contours[0].tabs==[10,20] and app.contours[0].start_s==7
        app.undo();assert [c.points for c in app.contours]==before
        app.redo();app.canvas.event_generate('<F>');app.update()
        assert all(abs(x-px)<1e-8 and abs(y-py)<1e-8 for c,points in zip(app.contours,before) for (x,y),(px,py) in zip(c.points,points))
        app.canvas.event_generate('<r>');app.update()
        assert [c.points for c in app.contours]!=before
        app.undo()
        app.manual_array_mode=False;app.canvas.event_generate('<f>');app.update()
        assert all(abs(x-px)<1e-8 and abs(y-py)<1e-8 for c,points in zip(app.contours,before) for (x,y),(px,py) in zip(c.points,points))
        print('QUANTITY_DELETE_GUI_OK')
    finally:app.destroy()
