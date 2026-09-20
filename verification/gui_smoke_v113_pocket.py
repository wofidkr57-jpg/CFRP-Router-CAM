"""Exercise pocket controls, rendering, settings persistence and NC generation on Windows."""
import os
import sys
import tempfile
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import cfrp_router_cam as cam

with tempfile.TemporaryDirectory() as folder:
    os.environ['CFRP_CAM_LANGUAGE']='en'
    cam.App.executable_dir=lambda self:folder
    cam.App.appdata_settings_path=lambda self:str(Path(folder)/'settings-fallback.json')
    app=cam.App();app.update_idletasks()
    assert not app.vars['wall_finish'].get()
    assert not app.vars['onion_skin_enabled'].get()
    assert app.vars['pocket_stay_down'].get()
    assert app.vars['path_tolerance'].get()==.01
    stock=[(0,0),(40,0),(40,30),(0,30)]
    island=[(15,10),(25,10),(25,20),(15,20)]
    c=cam.Contour(stock,operation='pocket',role='pocket',target_depth=.5,pocket_max_depth=.5,
                  pocket_holes=[island],pocket_stock=stock,tabs_enabled=False)
    app.set_single_part([cam.Contour(stock),c],'synthetic',3)
    app.vars['pocket_stepover'].set(35)
    app.vars['pocket_stepdown'].set(.2)
    app.vars['pocket_finish'].set(.05)
    app.vars['step_pockets'].set(False)
    app.redraw();app.update_idletasks()
    cfg=app.config()
    code=cam.generate_gcode(app.contours,cfg)
    assert '(ISLAND POCKET ' in code
    assert 'Pocket stay-down link' in code
    assert 'Pocket rough pass 3/3' in code
    app.save_settings();app.destroy()
    app=cam.App();app.update_idletasks()
    assert app.vars['pocket_stepover'].get()==35
    assert app.vars['pocket_stepdown'].get()==.2
    assert app.vars['pocket_finish'].get()==.05
    assert not app.vars['step_pockets'].get()
    app.destroy()
print('GUI_POCKET_V113_OK')
