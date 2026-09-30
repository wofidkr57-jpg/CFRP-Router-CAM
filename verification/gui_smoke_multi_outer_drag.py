"""Selected outer rows move as one block; list selection does not rebuild the scene."""
import os
import sys
import tempfile
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import cfrp_router_cam as cam


with tempfile.TemporaryDirectory() as tmp:
    os.environ["CFRP_CAM_LANGUAGE"] = "en"
    cam.App.executable_dir = lambda self: tmp
    cam.App.appdata_settings_path = lambda self: str(Path(tmp) / "fallback.json")
    app = cam.App()
    try:
        contours = []
        for i in range(5):
            x = i * 20.0
            contours.append(cam.Contour([(x, 0), (x+10, 0), (x+10, 10), (x, 10)],
                                        role="outer", layer=f"PART_{i}", outer_cut_order=i+1))
        app.contours = contours
        app.vars["show_toolpath"].set(False)
        app.redraw()
        app.update()
        tree = app.order_tree
        panel = tree.master.master
        panel.sashpos(0, 140)
        panel.sashpos(1, 520)
        app.update()
        assert tree.get_children() == tuple(f"c{i}" for i in range(5))
        tree.selection_set("c0", "c2")
        tree.focus("c0")
        with mock.patch.object(app, "redraw", side_effect=AssertionError("selection rebuilt the scene")):
            app.tree_select()
            before = app.canvas.find_all()
            assert app.contour_selection_items[0][3]["fill"] == "#42e695"
            assert app.contour_selection_items[2][3]["fill"] == "#42e695"
            tree.selection_set("c1", "c3")
            tree.focus("c1")
            app.tree_select()
            assert app.canvas.find_all() == before
            assert app.contour_selection_items[0][3]["fill"] != "#42e695"
            assert app.contour_selection_items[1][3]["fill"] == "#42e695"
        tree.selection_set("c0", "c2")
        tree.focus("c0")
        app.tree_select()
        source_box = tree.bbox("c0", "seq")
        target_box = tree.bbox("c4", "seq")
        assert source_box and target_box
        x = source_box[0] + source_box[2] // 2
        y = source_box[1] + source_box[3] // 2
        tree.event_generate("<Button-1>", x=x, y=y)
        app.update()
        assert set(tree.selection()) == {"c0", "c2"}
        event = SimpleNamespace(x=target_box[0]+10,
                                y=target_box[1]+target_box[3]-2, state=0)
        app.drag_outer_order(event)
        app.update()
        assert app.order_insert_line.winfo_ismapped()
        app.drop_outer_order(event)
        app.update()
        assert [c.layer for c in cam.ordered_contours(app.contours) if c.role == "outer"] == [
            "PART_1", "PART_3", "PART_4", "PART_0", "PART_2"]
        assert {c.layer for c in app.selected_contours} == {"PART_0", "PART_2"}
        assert not app.order_insert_line.winfo_ismapped()
        app.undo()
        assert [c.outer_cut_order for c in app.contours] == [1, 2, 3, 4, 5]
        print("MULTI_OUTER_DRAG_GUI_OK")
    finally:
        app.destroy()
