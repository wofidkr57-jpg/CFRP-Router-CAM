"""Headless rendering regression: no Tk window or machine connection."""
import unittest
import cfrp_router_cam as cam


class Var:
    def __init__(self, value): self.value = value
    def get(self): return self.value
    def set(self, value): self.value = value


class Canvas:
    def __init__(self):
        self.items = {}; self.serial = 0; self.clears = 0; self.width = 800
    def winfo_width(self): return self.width
    def winfo_height(self): return 600
    def create_line(self, *coords, **kw):
        self.serial += 1
        tags = kw.pop('tags', ())
        if isinstance(tags, str): tags = (tags,)
        self.items[self.serial] = dict(kw, tags=tags, coords=coords)
        return self.serial
    create_polygon = create_text = create_oval = create_line
    def matching(self, target):
        return [i for i, v in self.items.items()
                if target == 'all' or target == i or target in v['tags']]
    def delete(self, target):
        if target == 'all': self.clears += 1
        for i in self.matching(target): del self.items[i]
    def itemconfigure(self, target, **kw):
        for i in self.matching(target): self.items[i].update(kw)
    def tag_raise(self, *args): pass
    def tag_lower(self, *args): pass


class Harness:
    # Exercise the real projection, draw, progress and visibility methods.
    def winfo_exists(self): return True


for name, value in vars(cam.Toolpath3D).items():
    if name != '__init__' and (callable(value) or name.isupper()):
        setattr(Harness, name, value)


def viewer(count=12):
    v = Harness(); v.canvas = Canvas()
    v.moves = [cam.Move3D((i, 0, -1), (i+1, 0, -1), i % 4 == 0, 1)
               for i in range(count)]
    v.cfg = {'stock': 2, 'tool_d': 2}
    v.az = v.el = v.panx = v.pany = 0.; v.zoom = 1.
    v.bounds = v.data_bounds(); v.tab_move_indices = set(); v.depth_levels = [1]
    v.sim_mode = Var('깊이맵'); v.show_rapid = Var(True)
    v.cumulative = list(range(1, count+1)); v.total_time = count
    v.sim_time = count / 2; v.info = Var(''); v._scene_key = None
    return v


class SimulationCacheTests(unittest.TestCase):
    def test_repeated_modes_reuse_geometry(self):
        v = viewer(10000); v.draw()
        lines = tuple(v.move_items); depths = tuple(v.depth_items)
        for mode in ('Toolpath', 'Depth map', '공구경로', '깊이맵') * 3:
            v.sim_mode.set(mode); v.draw()
            self.assertEqual(tuple(v.move_items), lines)
            self.assertEqual(tuple(v.depth_items), depths)
        self.assertEqual(v.canvas.clears, 1)
        self.assertTrue(all(v.canvas.items[i]['state'] == 'hidden' for i in lines))

    def test_rapid_toggle_retains_ids_and_styles(self):
        v = viewer(); v.draw(); ids = tuple(v.move_items)
        v.sim_mode.set('Toolpath'); v.show_rapid.set(False); v.draw()
        for i, m in enumerate(v.moves):
            item = v.canvas.items[v.move_items[i]]
            self.assertEqual(item['state'], 'hidden' if m.rapid else 'normal')
        self.assertEqual(v.canvas.items[v.move_items[1]]['fill'], '#ff6257')
        v.show_rapid.set(True); v.draw()
        self.assertEqual(tuple(v.move_items), ids)
        self.assertEqual(v.canvas.items[v.move_items[0]]['state'], 'normal')

    def test_scrub_in_path_mode_keeps_depth_map_current(self):
        v = viewer(); v.draw(); v.sim_mode.set('Toolpath'); v.draw()
        v.sim_time = 11; v.update_frame()
        self.assertIsNotNone(v.depth_items[10])
        self.assertEqual(v.canvas.items[v.depth_items[10]]['state'], 'hidden')
        v.sim_mode.set('Depth map'); v.draw()
        self.assertEqual(v.canvas.items[v.depth_items[10]]['state'], 'normal')
        v.sim_time = 2; v.update_frame()
        self.assertIsNone(v.depth_items[10])
        self.assertEqual(v.canvas.items[v.move_items[10]]['fill'], '#303841')
        v.sim_time = 12; v.update_frame()
        self.assertIsNotNone(v.depth_items[10])

    def test_camera_and_resize_invalidate_once(self):
        v = viewer(); v.draw()
        for field in ('az', 'el', 'zoom', 'panx', 'pany'):
            previous = tuple(v.move_items)
            setattr(v, field, getattr(v, field)+.1); v.draw()
            self.assertNotEqual(tuple(v.move_items), previous)
            clears = v.canvas.clears; v.draw()
            self.assertEqual(v.canvas.clears, clears)
        v.canvas.width += 100; v.draw()
        self.assertEqual(v.canvas.clears, 7)


if __name__ == '__main__': unittest.main()
