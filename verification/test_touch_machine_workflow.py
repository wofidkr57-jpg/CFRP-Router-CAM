"""Touch workflow checks with no Tk window, COM connection, or real machine."""
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import cfrp_router_cam as cam
from verification.test_mach3_bridge import FakeMach3Document, FakeMach3Script


class Value:
    def __init__(self, value): self.value = value
    def get(self): return self.value
    def set(self, value): self.value = value


class FakeApp:
    job_signature = cam.App.job_signature

    def __init__(self, directory):
        self.directory = directory
        self.vars = {key: Value(value) for key, value in {
            "z_origin": "Bottom", "touch_probe_datum": "Bottom",
            "touch_probe_macro": "M881", "touch_support_height": 3.25,
            "touch_support_override": True,
            "touch_xy_mode": "fixture", "touch_origin_x": 0.0,
            "touch_origin_y": 0.0, "feed": 100.0,
        }.items()}
        self.status = Value("")
        self.contours = [cam.Contour([(0., 0.), (20., 0.), (20., 10.), (0., 10.)])]
        self.gcode = ""
        self.gcode_parts = []
        self.gcode_signature = None
        self.make_count = 0
        self.split = False

    def config(self):
        return dict(start_code="", **{key: value.get() for key, value in self.vars.items()})

    def make_gcode(self):
        self.make_count += 1
        self.gcode = "G21 G90 G54\nM30\n"
        self.gcode_parts = [("rough", "(ROUGH)\n" + self.gcode)]
        if self.split:
            self.gcode_parts.append(("finish", "(FINISH)\n" + self.gcode))
        self.gcode_signature = self.job_signature(self.config())

    def appdata_settings_path(self):
        return str(Path(self.directory) / "settings.json")


class FakeWorkspace(cam.TouchWorkspace):
    """Call production methods while replacing only UI transport and model input."""
    def __init__(self, app, bridge):
        self.app = app
        self.bridge = bridge
        self.busy = False
        self.pending_signature = None
        self.last_machine = None
        self.closed = False
        self.machine_status = Value("")
        self.coords = Value("")
        self.choices = []
        self.scheduled = []
        self.previews = []

    def refresh(self): pass

    def after(self, milliseconds, callback):
        self.scheduled.append((milliseconds, callback))

    def choose(self, title, choices, callback):
        self.choices.append((title, choices, callback))

    def select(self, value):
        self.choices[-1][2](value)

    def show_boundary_preview(self, bounds, cfg):
        self.previews.append((bounds, cfg))


class TouchMachineWorkflowTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.script = FakeMach3Script()
        self.bridge = cam.Mach3Bridge(connector=lambda: FakeMach3Document(self.script))
        self.bridge.connect()
        self.app = FakeApp(self.temp.name)
        self.ui = FakeWorkspace(self.app, self.bridge)
        self.dialog_patch = patch.object(cam.messagebox, "showerror")
        self.errors = self.dialog_patch.start()
        self.addCleanup(self.dialog_patch.stop)
        self.addCleanup(self.temp.cleanup)

    def tearDown(self):
        self.bridge.disconnect()

    def mutations(self):
        return [call for call in self.script.calls
                if call[0] in ("LoadFile", "DoOEMButton", "Code", "SetUserDRO")]

    def start_count(self):
        return self.mutations().count(("DoOEMButton", cam.Mach3Bridge.START_BUTTON))

    def load(self, label="test"):
        self.ui.send_program("G21 G90 G54\nM30\n", self.app.config(), label)

    def test_loading_finishes_before_one_start_and_repeat_tick_never_restarts(self):
        self.load()
        self.ui.tick()
        self.assertEqual(self.start_count(), 0)
        self.script.loading = False
        self.ui.tick()
        self.ui.tick()
        self.assertEqual(self.start_count(), 1)
        self.assertFalse(self.ui.busy)
        self.assertIsNone(self.ui.pending_signature)

    def test_second_cut_during_loading_does_not_generate_or_load_twice(self):
        self.ui.cut()
        self.ui.cut()
        self.assertEqual(self.app.make_count, 1)
        self.assertEqual(len([call for call in self.mutations() if call[0] == "LoadFile"]), 1)
        self.assertEqual(self.start_count(), 0)

    def test_setting_change_while_loading_cancels_start_without_machine_stop(self):
        self.load()
        self.app.vars["feed"].set(120.)
        self.script.loading = False
        self.ui.tick()
        self.assertEqual(self.start_count(), 0)
        self.assertIsNone(self.bridge.pending_path)
        self.assertFalse(self.ui.busy)
        self.assertFalse(any(call[0] == "DoOEMButton" for call in self.mutations()))

    def test_geometry_change_while_loading_cancels_start(self):
        self.load()
        self.app.contours[0].points[0] = (5., 5.)
        self.script.loading = False
        self.ui.tick()
        self.assertEqual(self.start_count(), 0)
        self.assertIsNone(self.bridge.pending_path)

    def test_stop_during_loading_cancels_app_intent_and_sends_only_stop(self):
        self.load()
        self.ui.stop()
        self.script.loading = False
        self.ui.tick()
        self.assertEqual(self.start_count(), 0)
        self.assertEqual([call for call in self.mutations() if call[0] == "DoOEMButton"],
                         [("DoOEMButton", cam.Mach3Bridge.STOP_BUTTON)])
        self.assertFalse(self.ui.busy)
        self.assertIsNone(self.ui.pending_signature)

    def test_hold_during_loading_does_not_leave_ui_waiting_forever(self):
        self.load()
        self.ui.hold()
        self.script.loading = False
        self.ui.tick()
        self.assertEqual(self.start_count(), 0)
        self.assertIsNone(self.bridge.pending_path)
        self.assertIsNone(self.ui.pending_signature)
        self.assertFalse(self.ui.busy)

    def test_user_stop_is_dispatched_even_if_reported_units_changed(self):
        self.script.leds[802] = 0
        self.ui.stop()
        self.assertEqual(self.mutations(), [("DoOEMButton", cam.Mach3Bridge.STOP_BUTTON)])

    def test_user_hold_is_dispatched_even_if_reported_units_changed(self):
        self.script.leds[802] = 0
        self.ui.hold()
        self.assertEqual(self.mutations(), [("DoOEMButton", cam.Mach3Bridge.HOLD_BUTTON)])

    def test_resume_during_loading_clears_pending_ui_and_sends_only_resume(self):
        self.load()
        self.ui.resume()
        self.script.loading = False
        self.ui.tick()
        self.assertIsNone(self.bridge.pending_path)
        self.assertIsNone(self.ui.pending_signature)
        self.assertFalse(self.ui.busy)
        self.assertEqual([call for call in self.mutations() if call[0] == "DoOEMButton"],
                         [("DoOEMButton", cam.Mach3Bridge.RESUME_BUTTON)])

    def test_unit_change_during_load_cancels_start(self):
        self.load()
        self.script.loading = False
        self.script.leds[802] = 0
        self.ui.tick()
        self.assertEqual(self.start_count(), 0)
        self.assertIsNone(self.ui.pending_signature)
        self.assertIsNone(self.bridge.pending_path)

    def test_coordinate_transform_change_during_load_cannot_start(self):
        for led in (10, 108):
            with self.subTest(led=led):
                self.script.leds[10] = self.script.leds[108] = 0
                self.load("transform_" + str(led))
                self.script.loading = False
                self.script.leds[led] = 1
                before = self.start_count()
                self.ui.tick()
                self.assertEqual(self.start_count(), before)
                self.assertIsNone(self.ui.pending_signature)

    def test_read_failure_clears_coordinates_and_pending_intent(self):
        self.load()
        self.ui.coords.set("X 10.000 Y 20.000 Z 6.000")
        self.script.fail_snapshot = True
        self.ui.tick()
        self.assertIsNone(self.ui.last_machine)
        self.assertIn("—", self.ui.coords.get())
        self.assertFalse(self.ui.busy)
        self.assertIsNone(self.ui.pending_signature)
        self.assertEqual(self.start_count(), 0)

    def test_macro_and_tool_change_are_not_reported_as_idle(self):
        for led in (162, 806):
            with self.subTest(led=led):
                self.script.leds[162] = self.script.leds[806] = 0
                self.script.leds[led] = 1
                self.ui.tick()
                self.assertNotIn(" · 대기 · ", self.ui.machine_status.get())

    def test_reconnect_clears_previous_pending_ui_request(self):
        self.load()
        replacement = cam.Mach3Bridge(connector=lambda: FakeMach3Document(self.script))
        with patch.object(cam, "Mach3Bridge", return_value=replacement):
            self.ui.connect()
        self.addCleanup(replacement.disconnect)
        self.assertIsNone(self.ui.pending_signature)
        self.assertFalse(self.ui.busy)
        self.script.loading = False
        self.ui.tick()
        self.assertEqual(self.start_count(), 0)

    def test_capture_origin_uses_machine_coordinates_without_machine_write(self):
        self.ui.capture_origin()
        self.assertEqual(self.app.vars["touch_origin_x"].get(), 100.)
        self.assertEqual(self.app.vars["touch_origin_y"].get(), 200.)
        self.assertEqual(self.app.vars["touch_xy_mode"].get(), "current")
        self.assertEqual(self.mutations(), [])

    def test_capture_origin_rejects_unhomed_and_transformed_coordinates(self):
        for led in (807, 808, 809, 10, 108):
            with self.subTest(led=led):
                self.script.leds[led] = 1
                self.ui.capture_origin()
                self.script.leds[led] = 0
                self.assertEqual(self.app.vars["touch_xy_mode"].get(), "fixture")
        self.assertEqual(self.mutations(), [])

    def test_m881_only_sends_gage_block_value_then_registered_macro(self):
        self.ui.height_dialog()
        self.ui.select("probe")
        self.assertEqual(self.mutations(), [("SetUserDRO", 1001, 3.25), ("Code", "M881")])

    def test_leading_zero_m881_is_normalized_and_keeps_gage_block_write(self):
        self.app.vars["touch_probe_macro"].set("m00881")
        self.ui.height_dialog()
        self.ui.select("probe")
        self.assertEqual(self.mutations(), [("SetUserDRO", 1001, 3.25), ("Code", "M881")])

    def test_probe_after_loading_cancels_cut_request_without_delayed_start(self):
        self.load()
        self.script.loading = False
        self.ui.height_dialog()
        self.ui.select("probe")
        self.ui.tick()
        self.assertEqual(self.start_count(), 0)
        self.assertIsNone(self.ui.pending_signature)
        self.assertIsNone(self.bridge.pending_path)
        self.assertFalse(self.ui.busy)
        self.assertEqual(self.mutations()[-2:], [("SetUserDRO", 1001, 3.25), ("Code", "M881")])

    def test_top_datum_does_not_dispatch_bottom_probe_macro(self):
        self.app.vars["z_origin"].set("Top")
        self.ui.height_dialog()
        self.ui.select("probe")
        self.assertEqual(self.mutations(), [])
        self.assertTrue(self.errors.called)

    def test_probe_keeps_existing_mach3_gage_block_without_explicit_override(self):
        self.app.vars["touch_support_override"].set(False)
        self.ui.height_dialog()
        self.ui.select("probe")
        self.assertEqual(self.mutations(), [("Code", "M881")])

    def test_bottom_startup_m881_gets_explicit_support_height_before_load(self):
        code="G21 G90 G54\nN20m00881\nM30\n"
        self.ui.send_program(code,self.app.config(),"startup")
        self.assertEqual(self.mutations(),[("SetUserDRO",1001,3.25),("LoadFile",self.bridge.pending_path)])
        self.assertEqual(Path(self.bridge.pending_path).read_text(encoding="utf-8"),code)
        self.assertEqual(self.start_count(),0)

    def test_bottom_startup_m881_keeps_existing_mach3_support_without_override(self):
        self.app.vars["touch_support_override"].set(False)
        self.ui.send_program("M881\nM30\n",self.app.config(),"startup")
        self.assertEqual(self.mutations(),[("LoadFile",self.bridge.pending_path)])

    def test_top_rejects_m881_in_actual_finish_code_even_without_start_code_macro(self):
        self.app.vars["z_origin"].set("Top")
        cfg=self.app.config()
        cfg["onion_start_code"]="M881"
        with self.assertRaisesRegex(ValueError,"M881"):
            self.ui.send_program("(FINISH)\nN10M0881P1\nM30\n",cfg,"finish")
        self.assertEqual(self.mutations(),[])

    def test_m881_mentions_in_comments_do_not_block_top_or_write_gage_block(self):
        self.app.vars["z_origin"].set("Top")
        code="(M881: previous\nbottom macro M0881)\nG21 G90 ; M0881 (unused\nM8810\nM30\n"
        self.ui.send_program(code,self.app.config(),"comments")
        self.assertEqual(self.mutations(),[("LoadFile",self.bridge.pending_path)])

    def test_invalid_explicit_support_height_blocks_nc_before_dro_or_load(self):
        for value in (-1.,float("nan"),float("inf"),float("-inf")):
            with self.subTest(value=value):
                self.app.vars["touch_support_height"].set(value)
                with self.assertRaises(ValueError):
                    self.ui.send_program("M881\nM30\n",self.app.config(),"invalid")
        self.assertEqual(self.mutations(),[])

    def test_missing_nc_or_failed_file_save_never_writes_gage_block(self):
        for code in (None,"","   "):
            with self.subTest(code=code):
                with self.assertRaises(ValueError):self.ui.send_program(code,self.app.config(),"empty")
        with patch("builtins.open",side_effect=OSError("cannot save NC")):
            with self.assertRaises(OSError):self.ui.send_program("M881\nM30\n",self.app.config(),"save_error")
        self.assertEqual(self.mutations(),[])

    def test_leading_zero_m881_cannot_bypass_bottom_datum_check(self):
        self.app.vars["z_origin"].set("Top")
        self.app.vars["touch_probe_datum"].set("Top")
        self.app.vars["touch_probe_macro"].set("M0881")
        self.ui.height_dialog()
        self.ui.select("probe")
        self.assertEqual(self.mutations(), [])

    def test_boundary_view_never_loads_or_moves_machine(self):
        with patch.object(cam, "touch_boundary_program", return_value=("(BOUNDARY)\nM30\n", (0., 0., 20., 10.))):
            self.ui.boundary()
        self.ui.select("view")
        self.assertEqual(self.mutations(), [])
        self.assertEqual(self.ui.previews[0][0], (0., 0., 20., 10.))

    def test_selected_boundary_loads_the_previewed_program_once(self):
        self.app.vars["touch_xy_mode"].set("current")
        code = "(BOUNDARY)\nM30\n"
        with patch.object(cam, "touch_boundary_program", return_value=(code, (0., 0., 20., 10.))):
            self.ui.boundary()
        self.ui.select("run")
        self.assertEqual(Path(self.bridge.pending_path).read_text(encoding="utf-8"), code)
        self.script.loading = False
        self.ui.tick()
        self.ui.tick()
        self.assertEqual(self.start_count(), 1)

    def test_boundary_rejects_geometry_change_since_selection_dialog_opened(self):
        self.app.vars["touch_xy_mode"].set("current")
        with patch.object(cam, "touch_boundary_program", return_value=("(OLD BOUNDARY)\nM30\n", (0., 0., 20., 10.))):
            self.ui.boundary()
        self.app.contours[0].points[0] = (200., 200.)
        self.ui.select("run")
        self.assertFalse(any(call[0] == "LoadFile" for call in self.mutations()))

    def test_fixture_boundary_is_visible_but_never_runs_unknown_origin_macro(self):
        with patch.object(cam, "touch_boundary_program", return_value=("(FIXTURE BOUNDARY)\nM30\n", (0., 0., 20., 10.))):
            self.ui.boundary()
        self.ui.select("run")
        self.assertEqual(len(self.ui.previews), 1)
        self.assertEqual(self.mutations(), [])
        self.assertIn("현재 위치", str(self.errors.call_args))

    def test_split_selection_rejects_old_code_after_new_job_is_generated(self):
        self.app.split = True
        self.ui.cut()
        old_item = self.ui.choices[-1][1][0][1]
        self.app.vars["feed"].set(125.)
        self.app.make_gcode()
        self.ui.select(old_item)
        self.assertFalse(any(call[0] == "LoadFile" for call in self.mutations()))

    def test_split_selection_loads_only_selected_stage_and_ignores_duplicate_while_pending(self):
        self.app.split = True
        self.ui.cut()
        selected = self.ui.choices[-1][1][1][1]
        self.ui.select(selected)
        self.ui.select(selected)
        self.assertEqual(Path(self.bridge.pending_path).read_text(encoding="utf-8"), selected[1])
        self.assertEqual(len([call for call in self.mutations() if call[0] == "LoadFile"]), 1)

    def test_stop_during_gcode_generation_prevents_later_load(self):
        original = self.app.make_gcode
        def generate_and_stop():
            original()
            self.ui.stop()
        self.app.make_gcode = generate_and_stop
        self.ui.cut()
        self.assertEqual(self.mutations(), [("DoOEMButton", cam.Mach3Bridge.STOP_BUTTON)])
        self.assertFalse(self.ui.busy)


if __name__ == "__main__":
    unittest.main()
