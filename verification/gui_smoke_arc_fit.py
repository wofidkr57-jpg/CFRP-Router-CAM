"""Real Tk smoke test for optional arc output and old job settings."""
import copy
import json
import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import cfrp_router_cam as cam


with tempfile.TemporaryDirectory() as folder:
    os.environ["CFRP_CAM_LANGUAGE"] = "en"
    cam.App.executable_dir = lambda self: folder
    cam.App.appdata_settings_path = lambda self: str(Path(folder) / "settings.json")
    app = cam.App()
    try:
        app.update_idletasks()
        assert app.vars["arc_fit_enabled"].get() is False
        previous = app.job_signature(app.config())
        app.vars["arc_fit_enabled"].set(True)
        assert app.job_signature(app.config()) != previous
        document = json.loads(json.dumps(app.job_document()))
        assert document["vars"]["arc_fit_enabled"] is True
        app.vars["arc_fit_enabled"].set(False)
        app.decode_job(document)
        app.apply_job_values(document)
        assert app.vars["arc_fit_enabled"].get() is True
        old_job = copy.deepcopy(document)
        old_job["vars"].pop("arc_fit_enabled")
        app.decode_job(old_job)
        app.apply_job_values(old_job)
        assert app.vars["arc_fit_enabled"].get() is False
        print("ARC_FIT_GUI_AND_JOB_OK")
    finally:
        app.destroy()
