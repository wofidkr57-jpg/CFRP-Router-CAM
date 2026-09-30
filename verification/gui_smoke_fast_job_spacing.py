"""Open a saved mixed-size layout, draw references, and space it with undo."""
import json
import os
import sys
import tempfile
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import cfrp_router_cam as cam


with tempfile.TemporaryDirectory() as tmp:
    os.environ["CFRP_CAM_LANGUAGE"] = "en"
    cam.App.executable_dir = lambda self: tmp
    cam.App.appdata_settings_path = lambda self: str(Path(tmp) / "fallback.json")
    app = cam.App()
    try:
        first = cam.Contour([(0, 0), (10, 0), (10, 10), (0, 10)],
                            object_id=1, instance_id=1, object_name="A")
        second = cam.Contour([(16, 0), (26, 0), (26, 10), (16, 10)],
                             object_id=2, instance_id=1, object_name="B")
        app.contours = [first, second]
        app.part_objects = [cam.PartObject(1, "A", [first]), cam.PartObject(2, "B", [second])]
        app.next_object_id = 3
        app.nest_active = True
        app.sheet_size = (30, 30)
        app.vars["sheet_w"].set(30)
        app.vars["sheet_h"].set(30)
        app.vars["array_gap"].set(2)
        app.vars["array_edge"].set(0)
        path = Path(tmp) / "mixed.cfrpcam"
        path.write_text(json.dumps(app.job_document(), ensure_ascii=False), encoding="utf-8")
        with mock.patch.object(app, "confirm_job_replace", return_value=True), \
             mock.patch.object(app, "redraw", wraps=app.redraw) as redraw, \
             mock.patch.object(cam, "tool_sweep_collisions", side_effect=AssertionError("collision on load")), \
             mock.patch.object(cam, "contour_toolpath_issues", side_effect=AssertionError("path check on load")):
            assert app.load_job_file(str(path))
        assert redraw.call_count == 1, redraw.call_count
        assert len(app.canvas.find_withtag("manual_offset")) == 2
        assert app.gcode == "" and app.collision_cache_key is None
        before = cam.contour_group_bounds_map(app.contours)
        app.even_manual_spacing()
        after = cam.contour_group_bounds_map(app.contours)
        assert abs(after[(1, 1)][0] - 1.0) < 1e-5, after
        assert abs(after[(2, 1)][0] - 19.0) < 1e-5, after
        assert abs(after[(2, 1)][2] - 29.0) < 1e-5, after
        assert app.manual_array_layout_issues() == (0, 0)
        app.undo()
        assert cam.contour_group_bounds_map(app.contours) == before
    finally:
        app.destroy()
print("FAST_JOB_SPACING_GUI_OK")
