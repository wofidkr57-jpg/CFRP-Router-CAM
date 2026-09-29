"""Dense manual arrays: selection reuses paths, picking and drag stay correct."""
import copy,math,os,sys,tempfile
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
        app.update()
        template=cam.Contour([(12+10*math.cos(i*2*math.pi/1024),5+3*math.sin(i*2*math.pi/1024))
                              for i in range(1024)],role='outer',object_id=1,instance_id=1,
                             object_name='Synthetic',tabs=[2.0],start_s=1.0,
                             bridges=[((5.,5.),(6.,5.))])
        app.part_objects=[cam.PartObject(1,'Synthetic',[copy.deepcopy(template)],quantity=30,quantity_set=True)]
        app.contours=[]
        for i in range(30):
            c=copy.deepcopy(template);c.instance_id=i+1
            c.points=[(x+(i%5)*25,y+(i//5)*10) for x,y in c.points]
            c.enabled=i!=1;app.contours.append(c)
        app.nest_active=True;app.manual_array_mode=True;app.sheet_size=(130,65)
        app.vars['show_toolpath'].set(True);app.view_initialized=False
        app.redraw();app.update_idletasks()
        def event(p,state=0):
            x,y=app.transform(p);return SimpleNamespace(x=x,y=y,state=state,widget=app.canvas)
        def click(p,state=0):
            e=event(p,state);app.canvas_press(e);app.canvas_left_release(e);app.update()
        original=copy.deepcopy(app.contours)
        items=app.canvas.find_all();offsets=app.canvas.find_withtag('manual_offset')
        offset_coords=[app.canvas.coords(i) for i in offsets]
        # Selecting, toggling Ctrl and empty-space clicks must not scan dense
        # paths, regenerate compensation or delete/recreate any Canvas item.
        with mock.patch.object(app,'redraw',side_effect=AssertionError('selection rebuilt scene')), \
             mock.patch.object(cam,'contour_group_bounds_map',side_effect=AssertionError('pick rescanned vertices')), \
             mock.patch.object(cam,'compensated_route',side_effect=AssertionError('rebuilt offset')):
            click((12,5));assert app.selected_instance_keys()=={(1,1)}
            click((37,5),4);assert app.selected_instance_keys()=={(1,1),(1,2)}
            click((12,5),4);assert app.selected_instance_keys()=={(1,2)}
            # Disabled selected contour restores grey when deselected.
            click((62,5));assert app.selected_instance_keys()=={(1,3)}
            for item,key,c,normal,current in app.manual_selection_items:
                if c is not None:
                    assert app.canvas.itemcget(item,'fill')==('#42e695' if key==(1,3) else normal['fill'])
            click((-100,-100));assert not app.selected_instance_keys()
        assert app.canvas.find_all()==items
        assert [app.canvas.coords(i) for i in offsets]==offset_coords
        assert app.contours==original
        # The old 15px near-edge pick still works outside the group box.
        assert app.manual_group_at((2-8/app.view[0],5))==(1,1)
        # Pending zoom/pan transforms are flushed before starting a group drag;
        # their delayed redraw must not reset an in-progress pixel movement.
        app.pan_start(event((12,5)))
        pan=event((12,5));pan.x+=15;pan.y+=9;app.pan_move(pan);app.pan_end(pan)
        e=event((12,5));app.canvas_press(e)
        assert app.view_transform_job is None
        moved=SimpleNamespace(x=e.x+app.view[0],y=e.y-app.view[0],state=0)
        app.canvas_left_drag(moved)
        with mock.patch.object(app,'redraw',side_effect=AssertionError('redraw interrupted drag')):
            app.finish_view_redraw()
        app.canvas_left_release(moved)
        assert app.manual_pick_bounds[(1,1)]==cam.contour_group_bounds(app.contours,(1,1))
        assert all(abs(x-ox-1)<1e-7 and abs(y-oy-1)<1e-7
                   for (x,y),(ox,oy) in zip(app.contours[0].points,original[0].points))
        app.undo();assert app.contours==original
        # Filtering, undo and rotation must rebuild picking bounds.
        app.view_only=[app.contours[2]];app.redraw(refresh_tree=False)
        assert set(app.manual_pick_bounds)=={(1,3)}
        assert app.manual_group_at((12,5)) is None
        app.view_only=None;app.redraw(refresh_tree=False);click((12,5))
        app.rotate_manual_array_selected()
        assert app.manual_pick_bounds[(1,1)]==cam.contour_group_bounds(app.contours,(1,1))
        app.undo();assert app.contours==original
        print('MANUAL_INTERACTION_GUI_OK')
    finally:app.destroy()
