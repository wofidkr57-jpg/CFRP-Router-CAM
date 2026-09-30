"""Real Tk checkbox, list/preview, and saved-job compatibility for bore-first order."""
import copy
import json
import os
import sys
import tempfile
from pathlib import Path

sys.path[:0] = [str(Path(__file__).resolve().parents[1]), str(Path(__file__).resolve().parent)]
import cfrp_router_cam as cam
from test_depth_first_order import sample


with tempfile.TemporaryDirectory() as tmp:
    os.environ["CFRP_CAM_LANGUAGE"] = "en"
    cam.App.executable_dir = lambda self: tmp
    cam.App.appdata_settings_path = lambda self: str(Path(tmp) / "fallback.json")
    app = cam.App()
    try:
        app.update()
        app.contours = sample()
        app.vars["tool_wear_enabled"].set(False)
        app.vars["sheet_w"].set(140)
        app.vars["sheet_h"].set(50)
        app.vars["tab_count"].set(0)
        app.view_initialized = False
        app.redraw()
        app.update()
        assert not app.vars["depth_first_order"].get()
        before = [c.layer for c in app.preview_order_cache]
        previous_signature = app.job_signature(app.config())
        app.vars["depth_first_order"].set(True)
        app.redraw()
        app.update()
        expected = ["BORE", "SHALLOW", "DEEP", "THROUGH", "OUTER"]
        shown = [app.contours[int(i[1:])].layer for i in app.order_tree.get_children()]
        assert shown == expected, shown
        assert [c.layer for c in app.preview_order_cache] == expected
        assert before != expected
        assert app.job_signature(app.config()) != previous_signature
        document = json.loads(json.dumps(app.job_document()))
        assert document["vars"]["depth_first_order"] is True
        app.vars["depth_first_order"].set(False)
        app.apply_job_values(document)
        assert app.vars["depth_first_order"].get() is True
        legacy = copy.deepcopy(document)
        legacy["vars"].pop("depth_first_order")
        app.decode_job(legacy)
        app.apply_job_values(legacy)
        assert app.vars["depth_first_order"].get() is False
        print("DEPTH_FIRST_ORDER_GUI_OK")
    finally:
        app.destroy()
