"""Preview bounds, markers, depth map and mode cache with G53/macro interruptions."""
import sys,tkinter as tk
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import cfrp_router_cam as cam
root=tk.Tk();root.withdraw()
try:
    code='G0 X0 Y0 Z5\nG1 Z-6 F500\nG1 X20\nM881\nG53 G0 Z-70\nG0 X40 Y10\nG0 Z5\nG1 Z-6\nG1 X60\nG53 G0 X605 Y775'
    omitted=[];moves=cam.parse_gcode_moves(code,omitted=omitted)
    view=cam.Toolpath3D(root,moves,dict(stock=6.,z_origin='Top',tool_d=2.,_preview_omitted=omitted))
    view.update()
    assert view.bounds==(0.,0.,-6.,60.,10.,5.),view.bounds
    assert len(view.canvas.find_withtag('restart_marker'))==1
    view.sim_time=view.total_time;view.update_frame()
    paths=list(view.move_items)
    view.sim_mode.set('공구경로');view.mode_changed();view.update()
    assert view.move_items==paths
    view.sim_mode.set('깊이맵');view.mode_changed();view.update()
    assert view.move_items==paths
    assert view.collect_depth_levels()==[6.],view.collect_depth_levels()
    view.close()
finally:root.destroy()
print('PREVIEW_COORDINATES_GUI_OK')
