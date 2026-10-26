"""Offline touch workspace checks with temporary settings and synthetic geometry."""
import copy
import json
import math
import os
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import cfrp_router_cam as cam


def descendants(parent):
    result = []
    for child in parent.winfo_children():
        result.append(child)
        result.extend(descendants(child))
    return result


def button(parent, label):
    result = [item for item in descendants(parent) if isinstance(item, cam.ttk.Button) and str(item.cget("text")) == label]
    assert len(result) == 1, (label, len(result))
    return result[0]


def popup(app, title=None):
    result = [item for item in app.winfo_children() if isinstance(item, cam.tk.Toplevel)
              and (title is None or item.title() == title)]
    assert len(result) == 1, [item.title() for item in result]
    return result[0]


def touch_number(app, value, window=None):
    win = window if window is not None else popup(app)
    win.update()
    for character in str(value):
        button(win, "±" if character == "-" else character).invoke()
    button(win, "적용").invoke()
    app.update()


def scroll_canvas(widget, workspace):
    current = widget.master
    while current is not workspace and current is not None:
        if isinstance(current, cam.tk.Canvas):
            return current
        current = current.master
    return None


with tempfile.TemporaryDirectory() as temp, mock.patch.dict(os.environ, {"CFRP_CAM_LANGUAGE": "ko"}), \
        mock.patch.object(cam.App, "executable_dir", return_value=temp), \
        mock.patch.object(cam.App, "appdata_settings_path", return_value=str(Path(temp)/"settings.json")), \
        mock.patch.object(cam.Mach3Bridge, "connect", side_effect=AssertionError("Live Mach3 is forbidden in UI smoke")):
    errors = []
    callbacks = []
    issues = []
    cam.messagebox.showerror = lambda title, message, **kwargs: errors.append((title, message))
    cam.messagebox.showinfo = lambda *args, **kwargs: None
    app = cam.App()
    app.report_callback_exception = lambda *args: callbacks.append(args)
    try:
        app.update()
        original_canvas = app.canvas
        app.enable_touch_mode()
        app.example()
        app.vars["tool_wear_enabled"].set(False)
        app.vars["stock"].set(3.)
        app.vars["extra"].set(.1)
        app.update()
        touch = app.touch_workspace
        assert touch.bridge is None and app.canvas is touch.canvas
        for requested in ("1280x800", "1600x1000", "1920x1080"):
            app.geometry(requested+"+0+0")
            app.update()
            for control in touch.buttons:
                if not control.winfo_exists():
                    continue
                label = str(control.cget("text"))
                if control.cget("textvariable"):
                    label = app.getvar(str(control.cget("textvariable")))
                if control.winfo_height() < 64:
                    issues.append((requested, "height", label, control.winfo_height()))
                font = cam.tkfont.Font(root=app, font=cam.ttk.Style(app).lookup(control.cget("style"), "font"))
                text_width = font.measure(str(label))
                if text_width+16 > control.winfo_width():
                    issues.append((requested, "text-width", label, text_width, control.winfo_width()))
                if scroll_canvas(control, touch) is None:
                    x = control.winfo_rootx()-app.winfo_rootx()
                    y = control.winfo_rooty()-app.winfo_rooty()
                    if x < 0 or y < 0 or x+control.winfo_width() > app.winfo_width() or y+control.winfo_height() > app.winfo_height():
                        issues.append((requested, "outside-window", label, x, y, control.winfo_width(), control.winfo_height()))
            assert touch.canvas.winfo_width() >= 650 and touch.canvas.winfo_height() >= 300
            # Settings below the initial viewport stay reachable with touch scroll buttons.
            form_scroll = scroll_canvas(button(touch, "기존 지그 원점 사용"), touch)
            form_scroll.yview_moveto(1.)
            app.update()
            assert form_scroll.yview()[1] > .99
            form_scroll.yview_moveto(0.)

        before = copy.deepcopy(app.contours)
        for _ in range(2):
            app.enable_advanced_mode()
            app.update()
            assert app.canvas is original_canvas and app.canvas.winfo_viewable()
            assert app.contours == before
            app.enable_touch_mode()
            app.update()
            assert app.canvas is touch.canvas and app.canvas.winfo_viewable()
            assert app.contours == before

        outer = next(c for c in app.contours if c.role == "outer")
        hole = next(c for c in app.contours if c.role == "inner")
        app.set_contour_selection([outer], outer)
        angle_before = copy.deepcopy(app.contours)
        button(touch, "+90°").invoke()
        assert app.contours != angle_before
        button(touch, "−90°").invoke()
        for old, new in zip(angle_before, app.contours):
            assert all(math.dist(p, q) < 1e-8 for p, q in zip(old.points, new.points))
        button(touch, "각도 입력").invoke()
        touch_number(app, 15)
        touch.rotate(-15)

        # Tap one outline to place a manual microtab through the canvas handlers.
        initial_tabs = len(outer.tabs)
        button(touch, "탭 추가").invoke()
        x, y = app.transform(cam.point_at(outer.points, 35., True)[0])
        event = SimpleNamespace(x=x, y=y, state=0)
        app.canvas_press(event)
        app.canvas_left_release(event)
        assert len(outer.tabs) == initial_tabs+1

        app.set_contour_selection([hole], hole)
        button(touch, "부분 깊이").invoke()
        button(popup(app), "탑에서 기본 깊이 지정").invoke()
        touch_number(app, 1.2)
        assert hole.target_depth == 1.2 and outer.target_depth is None
        button(touch, "부분 깊이").invoke()
        button(popup(app), "기존 깊이에 추가 (+mm)").invoke()
        touch_number(app, .3)
        assert hole.additional_depth == .3 and outer.additional_depth == 0
        assert cam.effective_contour_depth(hole, 3., .1) == 1.5

        # Touch settings are valid for the ordinary CAM path without controller I/O.
        config = app.config()
        assert config["stock"] == 3 and config["touch_aux"] == "legacy"
        code = cam.generate_gcode(app.contours, config)
        assert code and cam.parse_gcode_moves(code)
        assert not app.vars["touch_support_override"].get()
        touch.refresh()
        assert touch.support_label.get() == "Mach3 기존 값"
        support_fields = [control for control in descendants(touch) if isinstance(control, cam.ttk.Button)
                          and str(control.cget("textvariable")) == str(touch.support_label)]
        assert len(support_fields) == 1
        support_fields[0].invoke()
        button(popup(app), "두께 직접 입력").invoke()
        touch_number(app, 9.5)
        assert app.vars["touch_support_height"].get() == 9.5
        assert app.vars["touch_support_override"].get()
        assert touch.support_label.get() == "9.5"
        machine = app.capture_profile("machine")
        assert machine["vars"]["touch_support_height"] == 9.5
        assert machine["vars"]["touch_support_override"] is True
        assert machine["vars"]["touch_probe_datum"] in ("Top", "Bottom")
        assert app.save_profile("machine"), errors
        app.vars["touch_support_height"].set(2.)
        app.vars["touch_support_override"].set(False)
        assert app.load_profile("machine"), errors
        assert app.vars["touch_support_height"].get() == 9.5 and app.vars["touch_support_override"].get()
        assert app.save_current_settings(), errors
        saved = json.loads(Path(app.portable_settings_path()).read_text(encoding="utf-8"))
        assert saved["vars"]["touch_support_height"] == 9.5 and saved["vars"]["touch_support_override"] is True
        legacy_override = copy.deepcopy(machine)
        legacy_override["vars"].pop("touch_support_override")
        restored_override = app.validate_profile("machine", legacy_override)
        assert restored_override["vars"]["touch_support_override"] is False
        assert restored_override["vars"]["touch_support_height"] == 9.5
        legacy_machine = copy.deepcopy(machine)
        for key in cam.TOUCH_MACHINE_KEYS:
            legacy_machine["vars"].pop(key)
        restored_machine = app.validate_profile("machine", legacy_machine)
        assert all(restored_machine["vars"][key] == cam.TOUCH_DEFAULTS[key] for key in cam.TOUCH_MACHINE_KEYS)
        support_fields[0].invoke()
        button(popup(app), "Mach3 기존 값 유지").invoke()
        assert not app.vars["touch_support_override"].get()
        assert touch.support_label.get() == "Mach3 기존 값"
        assert app.vars["touch_support_height"].get() == 9.5
        assert app.save_current_settings(), errors
        saved = json.loads(Path(app.portable_settings_path()).read_text(encoding="utf-8"))
        assert saved["vars"]["touch_support_override"] is False
        app.vars["touch_material"].set("알루미늄")
        app.vars["touch_aux"].set("none")
        app.vars["touch_aux_reviewed"].set(True)  # Synthetic default M-code fixture only.
        setup = app.capture_profile("setup")
        assert setup["vars"]["touch_material"] == "알루미늄" and setup["vars"]["touch_aux"] == "none"
        assert app.save_profile("setup"), errors
        app.vars["touch_material"].set("카본")
        app.vars["touch_aux"].set("legacy")
        assert app.load_profile("setup"), errors
        assert app.vars["touch_material"].get() == "알루미늄" and app.vars["touch_aux"].get() == "none"
        legacy_setup = copy.deepcopy(setup)
        for key in cam.TOUCH_SETUP_KEYS:
            legacy_setup["vars"].pop(key)
        restored_setup = app.validate_profile("setup", legacy_setup)
        assert restored_setup["vars"]["touch_material"] == "카본" and restored_setup["vars"]["touch_aux"] == "legacy"
        app.vars["touch_material"].set("카본")
        app.vars["touch_aux"].set("legacy")
        app.vars["touch_aux_reviewed"].set(False)
        # Popups expose existing operations without requiring a machine connection.
        for opener in (touch.cutting_settings, touch.machine_dialog):
            opener()
            win = popup(app)
            win.update()
            for control in descendants(win):
                if not isinstance(control, cam.ttk.Button):
                    continue
                assert control.winfo_height() >= 64, (win.title(), control.cget("text"), control.winfo_height())
                assert control.winfo_rootx()-win.winfo_rootx()+control.winfo_width() <= win.winfo_width()
                assert control.winfo_rooty()-win.winfo_rooty()+control.winfo_height() <= win.winfo_height()
            if opener == touch.machine_dialog:
                for key, label, number in (("touch_probe_macro", "높이 측정 매크로", 883),
                                           ("touch_coolant_on", "절삭유 켜기", 8),
                                           ("touch_coolant_off", "절삭유 끄기", 9),
                                           ("touch_dust_on", "집진기 켜기", 890),
                                           ("touch_dust_off", "집진기 끄기", 891)):
                    existing = app.vars[key].get()
                    fields = [control for control in descendants(win) if isinstance(control, cam.ttk.Button)
                              and str(control.cget("textvariable")) == str(app.vars[key])]
                    assert len(fields) == 1
                    fields[0].invoke()
                    button(popup(app, label), "M 코드 번호 입력").invoke()
                    touch_number(app, number, popup(app, label+" (M 뒤 숫자)"))
                    assert app.vars[key].get() == f"M{number}"
                    fields[0].invoke()
                    button(popup(app, label), "미지정으로 비우기").invoke()
                    assert app.vars[key].get() == ""
                    app.vars[key].set(existing)
            button(win, "닫기").invoke()
        touch.height_dialog()
        button(popup(app), "기준면 직접 측정 안내").invoke()
        assert touch.bridge is None
        assert not errors, errors
        assert not callbacks, callbacks
        print("TOUCH_MAIN_LAYOUT", repr(issues), flush=True)
        if "--preview" in sys.argv:
            app.geometry("1600x1000+0+0")
            app.title("CFRP Router CAM - Touch QA - synthetic geometry")
            app.set_contour_selection([outer], outer)
            app.fit_view()
            app.update()
            print("TOUCH_MAIN_PREVIEW_READY", flush=True)
            app.after(180000, app.destroy)
            app.mainloop()
        assert not issues, issues
        print("GUI_TOUCH_MAIN_OK sizes=1280,1600,1920 canvas=roundtrip rotation=keypad tabs=manual depth=partial NC=offline")
    finally:
        try:
            exists = app.winfo_exists()
        except cam.tk.TclError:
            exists = False
        if exists:
            touch.closed = True
            app.destroy()
