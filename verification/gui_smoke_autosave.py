"""Five-minute job recovery and close-time save behavior, without machine I/O."""
import json
import os
import sys
import tempfile
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import cfrp_router_cam as cam


assert cam.JOB_AUTOSAVE_INTERVAL_MS == 300000
with tempfile.TemporaryDirectory() as tmp:
    os.environ["CFRP_CAM_LANGUAGE"] = "en"
    cam.App.executable_dir = lambda self: tmp
    cam.App.appdata_settings_path = lambda self: str(Path(tmp) / "settings.json")
    path = Path(tmp) / "original.cfrpcam"
    app = cam.App()
    try:
        app.update()
        app.example()
        with mock.patch.object(cam.filedialog, "asksaveasfilename", return_value=str(path)):
            assert app.save_job()
        saved = path.read_bytes()
        app.vars["feed"].set(550.)
        assert app.autosave_job()
        recovery = Path(app.autosave_path)
        assert recovery.parent == Path(tmp) / "autosave"
        assert path.read_bytes() == saved
        assert json.loads(recovery.read_text(encoding="utf-8"))["autosave"]["source_path"] == str(path)
        with mock.patch.object(cam.os, "replace", side_effect=OSError("write failed")):
            app.vars["feed"].set(600.)
            assert not app.autosave_job()
        assert json.loads(recovery.read_text(encoding="utf-8"))["vars"]["feed"] == 550.
        app.vars["feed"].set(575.)
        assert app.autosave_job()
        assert json.loads(recovery.read_text(encoding="utf-8"))["vars"]["feed"] == 575.
    finally:
        app.destroy()  # Simulate an unclean exit; preserve the recovery file.

    with mock.patch.object(cam.messagebox, "askyesno", return_value=True) as recovery_prompt:
        app = cam.App()
        app.update()
        assert recovery_prompt.called
    closed = False
    try:
        assert app.job_path == str(path)
        assert app.saved_job_snapshot is None
        assert app.vars["feed"].get() == 575.
        assert app.recovered_autosave_path == str(recovery)
        with mock.patch.object(cam.messagebox, "askyesnocancel", return_value=None) as close_prompt:
            app.on_close()
            assert close_prompt.called and app.winfo_exists() and recovery.exists()
        assert app.save_job()
        assert not recovery.exists()
        assert json.loads(path.read_text(encoding="utf-8"))["vars"]["feed"] == 575.
        app.vars["feed"].set(500.)
        assert app.autosave_job()
        with mock.patch.object(cam.messagebox, "askyesnocancel", return_value=False):
            app.on_close()
        closed = True
        assert not recovery.exists()
        assert not Path(app.autosave_path).exists()
    finally:
        if not closed:app.destroy()

    app = cam.App()
    app.update()
    try:
        app.example()
        assert app.autosave_job()
        unsaved_recovery = Path(app.autosave_path)
        destination = Path(tmp) / "20260930_작업.cfrpcam"
        with mock.patch.object(cam.messagebox, "askyesnocancel", return_value=True), \
             mock.patch.object(cam.filedialog, "asksaveasfilename", return_value=str(destination)):
            app.on_close()
        assert destination.is_file() and not unsaved_recovery.exists()
    finally:
        try:app.destroy()
        except cam.tk.TclError:pass
print("AUTOSAVE_GUI_OK")
