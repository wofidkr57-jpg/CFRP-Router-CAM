import importlib.util
import os
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "cfrp_router_cam.py"
if not SOURCE.is_file():
    SOURCE = ROOT / "CFRP_Router_CAM_V1.10_source" / "cfrp_router_cam.py"
SPEC = importlib.util.spec_from_file_location("carbon_cam_gui_smoke_v110", SOURCE)
cam = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = cam
SPEC.loader.exec_module(cam)


def has_hangul(text):
    return any("가" <= char <= "힣" for char in str(text))


with tempfile.TemporaryDirectory() as folder:
    os.environ["CFRP_CAM_LANGUAGE"] = "en"
    cam.App.executable_dir = lambda self: folder
    cam.App.appdata_settings_path = lambda self: str(Path(folder) / "appdata-settings.json")
    app = cam.App()
    app.update_idletasks()
    visible = []
    stack = [app]
    while stack:
        widget = stack.pop()
        stack.extend(widget.winfo_children())
        try:
            text = widget.cget("text")
            if text:
                visible.append((str(widget), str(text)))
        except Exception:
            pass
        try:
            values = widget.cget("values")
            visible.extend((str(widget), str(value)) for value in values)
        except Exception:
            pass
    leaks = [(name, text) for name, text in visible if has_hangul(text)]
    tab_row = int(app.manual_btn.grid_info()["row"])
    origin_row = int(app.origin_btn.grid_info()["row"])
    array_row = int(app.manual_array_btn.grid_info()["row"])
    app.destroy()
    if leaks:
        raise SystemExit("English UI contains Hangul: " + repr(leaks[:10]))
    if not tab_row < origin_row < array_row:
        raise SystemExit(f"Unexpected control order: tab={tab_row}, origin={origin_row}, array={array_row}")
    print(f"GUI_SMOKE_OK widgets={len(visible)} language=en tab={tab_row} origin={origin_row} array={array_row}")
