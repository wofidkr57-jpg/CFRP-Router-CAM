"""Verify the selected start marker points along the current profile direction."""
import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import cfrp_router_cam as cam


with tempfile.TemporaryDirectory() as tmp:
    os.environ["CFRP_CAM_LANGUAGE"] = "en"
    cam.App.executable_dir = lambda self: tmp
    cam.App.appdata_settings_path = lambda self: str(Path(tmp) / "fallback.json")
    app = cam.App()
    try:
        app.set_single_part([cam.Contour([(0, 0), (40, 0), (40, 20), (0, 20)])], "square.dxf")
        app.contours[0].start_s = 10.
        app.vars["show_toolpath"].set(True)
        for climb, sign in ((True, -1), (False, 1)):
            app.vars["climb"].set(climb)
            app.redraw()
            markers = [item for item in app.canvas.find_all()
                       if app.canvas.type(item) == "polygon"
                       and app.canvas.itemcget(item, "fill") == "#ff4fd8"]
            assert len(markers) == 1, markers
            coords = app.canvas.coords(markers[0])
            assert (coords[0] - (coords[2] + coords[4]) / 2) * sign > 0, coords
            paths = [item for item in app.canvas.find_all()
                     if app.canvas.type(item) == "line"
                     and app.canvas.itemcget(item, "fill") == "#ff6363"]
            assert len(paths) == 1, paths
            route = app.canvas.coords(paths[0])
            assert (route[2] - route[0]) * sign > 0, route[:4]
    finally:
        app.destroy()
print("START_ARROW_GUI_OK")
