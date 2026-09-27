"""Exercise CAM viewer routing only; browser and GPU are not launched."""
import os,sys,tempfile
from pathlib import Path
from unittest import mock
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import cfrp_router_cam as cam

with tempfile.TemporaryDirectory() as folder:
    with mock.patch.dict(os.environ,{'CFRP_CAM_LANGUAGE':'ko','APPDATA':folder}), \
         mock.patch.object(cam,'application_directory',return_value=folder):
        app=cam.App()
        try:
            app.update()
            settings=app.config()
            app.gcode='G0 X0 Y0 Z5\nG1 Z-2 F500\nG1 X10'
            app.gcode_parts=[]
            app.gcode_signature=app.job_signature(settings)
            with mock.patch.object(cam,'open_gpu_viewer',return_value='mock-local-viewer.html') as gpu, \
                 mock.patch.object(cam,'Toolpath3D') as classic:
                app.open_3d()
                assert gpu.call_count==1 and classic.call_count==0
                assert len(gpu.call_args.args[0])>0
                buttons=[];stack=[app]
                while stack:
                    widget=stack.pop();stack.extend(widget.winfo_children())
                    if isinstance(widget,cam.ttk.Button) and widget.cget('text')=='기본 3D 뷰어 열기':buttons.append(widget)
                assert len(buttons)==1
                buttons[0].invoke()
                assert classic.call_count==1 and gpu.call_count==1
                gpu.side_effect=OSError('test browser unavailable')
                app.open_3d()
                assert classic.call_count==2
        finally:app.destroy()
print('GPU_VIEWER_ROUTING_GUI_OK default, classic button, launch failure; browser not launched')
