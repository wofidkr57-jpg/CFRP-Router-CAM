"""Native GPU geometry and routing, without loading a driver or controlling CNC."""
import inspect,math,unittest
import numpy as np
import cfrp_router_cam as cam


class GPUViewerTests(unittest.TestCase):
    def batches(self,moves,**changes):
        cfg=dict(stock=6,tool_d=2,z_origin='Top');cfg.update(changes)
        return cam.native_toolpath_buffers(moves,cfg,lambda d:'#00D9FF',{1})

    def test_discontinuities_bounds_and_time(self):
        moves=cam.parse_gcode_moves('G0 X0 Y0 Z5\nG1 Z-2 F500\nG1 X10\nM881\nG53 G0 Z-70\nG0 X20 Y10\nG0 Z5\nG1 Z-2\nG1 X30')
        b=self.batches(moves)
        np.testing.assert_allclose(b['line'][::2,:3],[m.start for m in moves])
        np.testing.assert_allclose(b['line'][1::2,:3],[m.end for m in moves])
        self.assertEqual(len(b['markers']),1)
        self.assertEqual(b['bounds'],(0,0,-2,30,10,5))
        self.assertAlmostEqual(b['total'],sum(m.seconds for m in moves))
        self.assertAlmostEqual(float(b['line'][-1,3]),b['total'],places=5)

    def test_depth_width_colour_tabs_and_no_rapid_sweep(self):
        moves=[cam.Move3D((0,0,-2),(10,0,-2),False,1),
               cam.Move3D((10,0,-2),(20,0,-2),False,1),
               cam.Move3D((20,0,-2),(30,0,-2),True,1)]
        b=self.batches(moves)
        self.assertEqual(b['depth'].shape,(12,9));self.assertEqual(b['tabs'].shape,(2,9))
        self.assertEqual(b['depth'][:,1].min(),-1);self.assertEqual(b['depth'][:,1].max(),1)
        np.testing.assert_allclose(b['depth'][:,2],0);np.testing.assert_allclose(b['depth'][:,4],2)
        np.testing.assert_allclose(b['depth'][0,6:],[0,217/255,1])
        bottom=self.batches([cam.Move3D((0,0,4),(10,0,4),False,1)],z_origin='Bottom')
        np.testing.assert_allclose(bottom['depth'][:,2],6);np.testing.assert_allclose(bottom['depth'][:,4],2)

    def test_large_batch_and_validation(self):
        b=self.batches([cam.Move3D((i,0,-2),(i+1,0,-2),False,.1) for i in range(20000)])
        self.assertEqual(b['line'].shape,(40000,9));self.assertEqual(b['depth'].shape,(120000,9))
        for name in ('line','depth','stock','tabs','markers'):
            self.assertEqual(b[name].dtype,np.float32);self.assertTrue(b[name].flags.c_contiguous)
            self.assertTrue(np.isfinite(b[name]).all())
        for moves,cfg in (([],{}),([cam.Move3D((0,0,math.nan),(1,0,-2),False,1)],{}),
                          ([cam.Move3D((0,0,-2),(1,0,-2),False,-1)],{}),
                          ([cam.Move3D((0,0,-2),(1,0,-2),False,1)],{'tool_d':0})):
            with self.assertRaises(ValueError):self.batches(moves,**cfg)

    def test_application_has_no_browser_launcher(self):
        source=inspect.getsource(cam)
        self.assertNotIn('webbrowser',source);self.assertNotIn('GPU_VIEWER_HTML',source)
        self.assertIn('NativeToolpath3D(self,moves,cfg)',inspect.getsource(cam.App.open_3d))


if __name__=='__main__':unittest.main()
