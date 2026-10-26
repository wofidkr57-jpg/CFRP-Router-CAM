"""Exercise the touch STEP setup using synthetic geometry, without a device."""
import copy
import importlib.util
import math
import sys
from pathlib import Path
from types import SimpleNamespace


SOURCE = Path(__file__).resolve().parents[1] / "cfrp_router_cam.py"
SPEC = importlib.util.spec_from_file_location("cam_touch_step_smoke", SOURCE)
cam = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = cam
SPEC.loader.exec_module(cam)


def make_model():
    faces = []
    for x0, x1 in ((10., 30.), (30., 50.)):
        points = [(x0, 20., 3.), (x1, 20., 3.), (x1, 40., 3.), (x0, 40., 3.)]
        faces.append(cam.StepFace(points, [(0, 1, 2), (0, 2, 3)], (0., 0., 1.), ((x0+x1)/2, 30., 3.)))
    bottom = [(10., 20., 0.), (50., 20., 0.), (50., 40., 0.), (10., 40., 0.)]
    faces.append(cam.StepFace(bottom, [(0, 2, 1), (0, 3, 2)], (0., 0., -1.), (30., 30., 0.)))
    vertices = list(dict.fromkeys(point for face in faces for point in face.vertices))
    return cam.StepModel("synthetic-touch-plate.step", faces, vertices, face_components=[0, 0, 0], component_vertices={0: vertices})


def widgets(parent):
    result = []
    for child in parent.winfo_children():
        result.append(child)
        result.extend(widgets(child))
    return result


def button(parent, text):
    matches = [widget for widget in widgets(parent)
               if isinstance(widget, cam.ttk.Button) and str(widget.cget("text")) == text]
    assert len(matches) == 1, (text, len(matches))
    return matches[0]


def popup(dialog):
    result = [widget for widget in dialog.winfo_children() if isinstance(widget, cam.tk.Toplevel)]
    assert len(result) == 1
    return result[0]


def close_dialog(dialog):
    for name in ("step_draw_job", "step_exact_job"):
        job = getattr(dialog, name, None)
        if job is not None:
            dialog.after_cancel(job)
            setattr(dialog, name, None)
    dialog.cancel()


root = cam.tk.Tk()
root.geometry("800x600+20+20")
root._touch_active = True
root.vars = {"step_pockets": cam.tk.BooleanVar(root, value=True)}
errors = []
cam.messagebox.showerror = lambda title, message, **kwargs: errors.append((title, message))
cam.messagebox.showinfo = lambda *args, **kwargs: None
try:
    for language in ("ko", "en"):
        cam.CURRENT_LANGUAGE = language
        applied = []
        dialog = cam.StepSetupDialog(root, make_model(), lambda *args: applied.append(args))
        for size in ("980x700", "1280x800", "920x650"):
            dialog.geometry(size+"+20+20")
            dialog.update()
            for control in dialog.touch_buttons:
                assert control.winfo_ismapped(), (size, control.cget("text"))
                assert control.winfo_height() >= 64, (size, control.cget("text"), control.winfo_height())
                right = control.winfo_rootx()-dialog.winfo_rootx()+control.winfo_width()
                bottom = control.winfo_rooty()-dialog.winfo_rooty()+control.winfo_height()
                assert right <= dialog.winfo_width(), (size, control.cget("text"), right)
                assert bottom <= dialog.winfo_height(), (size, control.cget("text"), bottom)
                font = cam.tkfont.Font(root=dialog, font=cam.ttk.Style(dialog).lookup(control.cget("style"), "font"))
                assert font.measure(control.cget("text"))+18 <= control.winfo_width(), (size, control.cget("text"), font.measure(control.cget("text")), control.winfo_width())
            assert dialog.canvas.winfo_height() >= 220, (size, dialog.canvas.winfo_height())
        if language == "en":
            for widget in widgets(dialog):
                try:
                    text = str(widget.cget("text"))
                except cam.tk.TclError:
                    continue
                assert not any("가" <= char <= "힣" for char in text), text

        # Tap rendered face centres and toggle additional face selection without Ctrl.
        dialog.set_view(0, 0)
        def tap_face(index):
            x, y, _ = dialog.project(dialog.transformed_face_center(index), dialog.data_bounds())
            dialog.pick_at(SimpleNamespace(x=x, y=y, state=0))
        tap_face(0)
        assert dialog.selected_faces == [0]
        dialog.touch_mode_buttons["add"].invoke()
        tap_face(1)
        assert set(dialog.selected_faces) == {0, 1}
        tap_face(1)
        assert dialog.selected_faces == [0]
        dialog.touch_mode_buttons["add"].invoke()
        button(dialog, dialog._touch_text("탑면 +Z / Z0", "Top +Z / Z0")).invoke()
        assert dialog.face_aligned and dialog.mode.get() == "vertex"
        assert abs(dialog.transformed_face_center(0)[2]) < 1e-9

        # Large origin preset controls call the same geometric transform as advanced mode.
        button(dialog, dialog._touch_text("원점 위치", "Origin preset")).invoke()
        choice = popup(dialog)
        choice.update()
        button(choice, dialog._touch_text("좌하단", "Bottom left")).invoke()
        assert dialog.work_origin_set
        assert cam.v3_len(dialog.transformed_vertices()[0]) < 1e-9

        before = copy.deepcopy(dialog.model.matrix)
        button(dialog, dialog._touch_text("+90° 회전", "Rotate +90°")).invoke()
        button(dialog, dialog._touch_text("−90° 회전", "Rotate −90°")).invoke()
        assert all(abs(a-b) < 1e-9 for row_a, row_b in zip(before, dialog.model.matrix) for a, b in zip(row_a, row_b))
        button(dialog, dialog._touch_text("각도 입력", "Set angle")).invoke()
        keypad = popup(dialog)
        keypad.update()
        button(keypad, "4").invoke()
        button(keypad, "5").invoke()
        button(keypad, dialog._touch_text("회전 적용", "Apply rotation")).invoke()
        assert dialog.rotation.get() == 45
        expected = cam.mat_mul(cam.mat_rotate_z(45), before)
        assert all(abs(a-b) < 1e-9 for row_a, row_b in zip(expected, dialog.model.matrix) for a, b in zip(row_a, row_b))
        button(dialog, dialog._touch_text("각도 입력", "Set angle")).invoke()
        keypad = popup(dialog)
        keypad.update()
        button(keypad, "±").invoke()
        button(keypad, "4").invoke()
        button(keypad, "5").invoke()
        button(keypad, dialog._touch_text("회전 적용", "Apply rotation")).invoke()
        assert dialog.rotation.get() == -45
        assert all(abs(a-b) < 1e-9 for row_a, row_b in zip(before, dialog.model.matrix) for a, b in zip(row_a, row_b))

        # Drag mode continues to translate the existing model in its work XY plane.
        dialog.touch_mode_buttons["move"].invoke()
        before = copy.deepcopy(dialog.model.matrix)
        scale = dialog.screen_scale
        dialog.left_press(SimpleNamespace(x=100, y=100))
        dialog.left_move(SimpleNamespace(x=130, y=115))
        dialog.left_release(SimpleNamespace(x=130, y=115))
        assert math.isclose(dialog.model.matrix[0][3]-before[0][3], 30/scale)
        assert math.isclose(dialog.model.matrix[1][3]-before[1][3], -15/scale)

        original_zoom = dialog.zoom
        button(dialog, dialog._touch_text("확대 +", "Zoom +")).invoke()
        assert dialog.zoom > original_zoom
        button(dialog, dialog._touch_text("축소 −", "Zoom −")).invoke()
        assert math.isclose(dialog.zoom, original_zoom)
        button(dialog, dialog._touch_text("화면 맞춤", "Fit view")).invoke()
        assert dialog.zoom == 1 and dialog.panx == dialog.pany == 0
        dialog.touch_mode_buttons["pockets"].invoke()
        assert not root.vars["step_pockets"].get()
        dialog.touch_mode_buttons["pockets"].invoke()
        assert root.vars["step_pockets"].get()
        dialog.update()
        button(dialog, dialog._touch_text("CAM으로 가져오기", "Import into CAM")).invoke()
        assert not errors, errors
        assert len(applied) == 1 and len(applied[0][0]) == 1
        assert math.isclose(applied[0][4], 3.)
        root.update()

    # Existing toolbar remains available when the parent uses advanced mode.
    root._touch_active = False
    cam.CURRENT_LANGUAGE = "ko"
    advanced = cam.StepSetupDialog(root, make_model(), lambda *args: None)
    advanced.update()
    assert not advanced.touch_mode and not hasattr(advanced, "touch_panel")
    assert button(advanced, "선택면 → +Z / Z0").winfo_ismapped()
    close_dialog(advanced)
    print("GUI_TOUCH_STEP_OK languages=ko,en sizes=920,980,1280 selection=toggle alignment=+Z origin=XY0 rotation=keypad drag=XY import=3mm advanced=preserved")
finally:
    root.destroy()
