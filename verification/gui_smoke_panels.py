"""Responsive settings width and draggable panel geometry on real Tk."""
import os,sys,tempfile
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import cfrp_router_cam as cam

with tempfile.TemporaryDirectory() as tmp:
    os.environ['CFRP_CAM_LANGUAGE']='ko'
    cam.App.executable_dir=lambda self:tmp
    cam.App.appdata_settings_path=lambda self:str(Path(tmp)/'fallback.json')
    app=cam.App()
    try:
        app.update();app.geometry('1600x900');app.update();app.reset_panel_widths();app.update()
        assert app.control_canvas.winfo_width()>=app.controls_min_width()
        for widget in app.controls.winfo_children():
            if widget.winfo_class() in ('TEntry','TCombobox'):
                assert widget.winfo_x()+widget.winfo_width()<=app.controls.winfo_width(),widget
        pan=app.main_pan
        pan.sashpos(0,250);pan.sashpos(1,1000);app.remember_panel_widths();app.update()
        assert app.control_xscroll.winfo_ismapped()
        ratios=app.panel_ratios
        app.geometry('1200x800');app.update()
        assert abs(pan.sashpos(0)/pan.winfo_width()-ratios[0])<.01
        app.control_canvas.xview_moveto(1);app.update()
        assert app.control_canvas.xview()[0]>0
        app.state('zoomed');app.update();app.reset_panel_widths();app.update()
        assert app.control_canvas.xview()[0]==0
        for size in (10,14):
            app.font_size_var.set(size);app.apply_font_size();app.update()
            assert app.controls.winfo_width()>=app.controls_min_width()
        print('PANELS_GUI_OK',app.winfo_width(),app.control_canvas.winfo_width(),app.controls_min_width())
    finally:app.destroy()
