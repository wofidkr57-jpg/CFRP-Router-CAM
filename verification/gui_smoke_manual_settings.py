"""Manual startup defaults, isolated from job/profile persistence and UI language."""
import os
import sys
import tempfile
from pathlib import Path
from unittest import mock

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import cfrp_router_cam as cam

with tempfile.TemporaryDirectory() as tmp, mock.patch.dict(os.environ,{"CFRP_CAM_LANGUAGE":"en"}), mock.patch.object(cam.App,"executable_dir",return_value=tmp), mock.patch.object(cam.App,"appdata_settings_path",return_value=str(Path(tmp)/"settings.json")):
    app=cam.App();app.update()
    original=app.vars["full_depth"].get()
    saved=Path(tmp,"settings.json").read_bytes()
    app.vars["full_depth"].set(not original)
    app.save_settings(preserve_saved=True)  # updater/language path
    assert Path(tmp,"settings.json").read_bytes()==saved
    app.update()
    with mock.patch.object(app,"confirm_job_replace",return_value=True):app.on_close()
    app=cam.App();app.update()
    assert app.vars["full_depth"].get()==original
    app.vars["full_depth"].set(not original)
    assert app.save_current_settings()
    baseline=Path(tmp,"settings.json").read_bytes()
    app.vars["full_depth"].set(original)
    with mock.patch.object(app,"write_settings_file",side_effect=OSError("read-only")),mock.patch.object(cam.messagebox,"showerror"):
        assert not app.save_current_settings()
    app.save_settings(preserve_saved=True)
    assert Path(tmp,"settings.json").read_bytes()==baseline
    app.update()
    with mock.patch.object(app,"confirm_job_replace",return_value=True):app.on_close()
    app=cam.App();app.update()
    assert app.vars["full_depth"].get()==(not original)
    app.destroy()
print("MANUAL_SETTINGS_GUI_OK")
