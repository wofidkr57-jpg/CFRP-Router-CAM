"""Native shader/batch/readback on capable Windows GPUs, safe fallback on CI."""
import json,sys,time
from unittest import mock
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import cfrp_router_cam as cam
import numpy as np

root=cam.tk.Tk();root.withdraw();view=None
try:
    # Synthetic parallel strips with one discontinuity; no private inputs.
    moves=[cam.Move3D((i%200,i//200,-2),(i%200+1,i//200,-2),False,.01,restart=i==10000) for i in range(20000)]
    started=time.perf_counter()
    try:view=cam.NativeToolpath3D(root,moves,dict(stock=6.,tool_d=2.,z_origin='Top'))
    except (OSError,RuntimeError,ValueError,cam.tk.TclError) as exc:
        # Hosted CI may expose only Microsoft's OpenGL 1.1 software renderer.
        classic=cam.Toolpath3D(root,moves[:20],dict(stock=6.,tool_d=2.,z_origin='Top'))
        classic.update();classic.close()
        print('NATIVE_GPU_UNAVAILABLE_CLASSIC_OK',str(exc))
    else:
        view.update();init_ms=(time.perf_counter()-started)*1000
        gpu=view.gpu;assert gpu is not None
        uploads=gpu.uploads;handles=[v[0].value for v in gpu.buffers.values()]
        pixels=view.draw(readback=True);assert pixels is not None
        assert np.unique(pixels.reshape(-1,3),axis=0).shape[0]>3
        for i in range(10):
            view.sim_mode.set('공구경로' if i%2 else '깊이맵');view.mode_changed()
            view.az+=.01;view.zoom+=.01;view.panx+=1;view.draw()
            assert view.gpu is gpu and gpu.uploads==uploads
            assert [v[0].value for v in gpu.buffers.values()]==handles
            assert gpu.draw_calls<=5
        view.scrub('50.005');assert not view.playing;assert abs(view.current_point()[0]-.5)<.01
        view.play();assert view.playing;view.pause();view.stop();assert view.sim_time==0
        view.geometry('850x600');view.update();view.draw();assert gpu.uploads==uploads
        print('NATIVE_GPU_GUI_OK',json.dumps(dict(renderer=gpu.renderer,moves=len(moves),uploads=uploads,
                                                 draw_calls=gpu.draw_calls,initial_ms=round(init_ms,1))))
        view.close();view=None;assert gpu.closed and gpu.context is None and gpu.hdc is None
        second=cam.NativeToolpath3D(root,moves[:20],dict(stock=6.,tool_d=2.,z_origin='Top'))
        second.update();second_gpu=second.gpu
        with mock.patch.object(second_gpu,'draw',side_effect=RuntimeError('test GPU failure')):second.draw()
        assert second_gpu.closed
        fallback=[w for w in root.winfo_children() if isinstance(w,cam.Toolpath3D)]
        assert len(fallback)==1 and not isinstance(fallback[0],cam.NativeToolpath3D)
        fallback[0].close();root.update()
finally:
    if view is not None:view.close()
    root.destroy()
