"""Exercise the real Tk first-run modal with no settings, then relaunch.

Run separately for ko, en and close. CFRP_CAM_TEST_SOURCE can select an older
source to demonstrate the regression without changing the application.
"""
import importlib.util
import json
import os
import sys
import tempfile
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "cfrp_router_cam.py"
if not SOURCE.is_file():
    SOURCE = ROOT / "CFRP_Router_CAM_V1.10_source" / "cfrp_router_cam.py"
SOURCE = Path(os.environ.get("CFRP_CAM_TEST_SOURCE", SOURCE))
SPEC = importlib.util.spec_from_file_location("carbon_cam_first_run", SOURCE)
cam = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = cam
SPEC.loader.exec_module(cam)
choice = sys.argv[1] if len(sys.argv) > 1 else "en"
assert choice in ("ko", "en", "close")
expected = "ko" if choice == "close" else choice
errors = []
observations = []
original_choose = cam.choose_interface_language


def exercise_dialog(parent):
    def inspect_and_choose():
        dialogs = [child for child in parent.winfo_children()
                   if isinstance(child, cam.tk.Toplevel)]
        if len(dialogs) != 1:
            errors.append(f"Expected one language dialog, found {len(dialogs)}")
            parent.destroy()
            return
        dialog = dialogs[0]
        try:
            observations.append({"root": parent.state(), "dialog": dialog.state(),
                                 "viewable": dialog.winfo_viewable(),
                                 "transient": str(dialog.transient())})
            assert parent.state() == "withdrawn", observations[-1]
            assert dialog.winfo_viewable(), observations[-1]
            assert dialog.state() == "normal", observations[-1]
            assert not dialog.transient(), observations[-1]
            assert dialog.grab_current() == dialog
            buttons = [widget for frame in dialog.winfo_children()
                       for widget in frame.winfo_children()
                       if isinstance(widget, cam.ttk.Button)]
            assert {button.cget("text") for button in buttons} == {"한국어", "English"}
            if choice == "close":
                dialog.tk.call(dialog.protocol("WM_DELETE_WINDOW"))
            else:
                label = "English" if choice == "en" else "한국어"
                next(button for button in buttons if button.cget("text") == label).invoke()
        except Exception as exc:
            errors.append(repr(exc))
            if dialog.winfo_exists():
                dialog.destroy()

    parent.after(250, inspect_and_choose)
    return original_choose(parent)


with tempfile.TemporaryDirectory(prefix="cfrp-first-run-") as folder:
    with mock.patch.dict(os.environ, {"APPDATA": str(Path(folder) / "appdata")}):
        os.environ.pop("CFRP_CAM_LANGUAGE", None)
        with mock.patch.object(cam, "application_directory", return_value=folder):
            assert cam.saved_interface_language() is None
            with mock.patch.object(cam, "choose_interface_language", side_effect=exercise_dialog):
                app = cam.App()
            app.update()
            try:
                assert not errors, errors
                assert app.winfo_viewable()
                assert app.language == expected
                settings = json.loads((Path(folder) / "settings.json").read_text(encoding="utf-8"))
                assert settings["language"] == expected
                assert settings["version"] == cam.APP_VERSION
            finally:
                app.destroy()
            cam.CURRENT_LANGUAGE = "ko"
            with mock.patch.object(cam, "choose_interface_language", side_effect=AssertionError("Prompt repeated")):
                restarted = cam.App()
            restarted.update()
            try:
                assert restarted.winfo_viewable()
                assert restarted.language == expected
                assert cam.CURRENT_LANGUAGE == expected
            finally:
                restarted.destroy()
print(f"FIRST_RUN_OK choice={choice} observations={observations} saved={expected} restart=OK")
