"""Mach3 protocol boundary tests. Every test uses an in-memory fake, never COM."""
import os
import tempfile
import threading
import unittest

import cfrp_router_cam as cam


class FakeMach3Script:
    def __init__(self):
        self.calls = []
        self.leds = {802: 1}
        self.dros = {83: 100.0, 84: 200.0, 85: -70.0,
                     178: 10.0, 179: 20.0, 180: 6.0,
                     800: -999.0, 801: -999.0, 802: -999.0,
                     118: 0.0, 816: 0.0}
        self.filename = "No File Loaded."
        self.loading = False
        self.moving = False
        self.fail_button = None
        self.fail_snapshot = False

    def GetActiveProfileName(self):
        self.calls.append(("GetActiveProfileName",))
        if self.fail_snapshot:
            raise RuntimeError("Mach3 process gone")
        return "Mach3Mill"

    def FileName(self):
        self.calls.append(("FileName",))
        return self.filename

    def GetOEMDRO(self, number):
        self.calls.append(("GetOEMDRO", number))
        return self.dros.get(number, 0.0)

    def GetOEMLED(self, number):
        self.calls.append(("GetOEMLED", number))
        return self.leds.get(number, 0)

    def IsLoading(self):
        self.calls.append(("IsLoading",))
        return int(self.loading)

    def IsMoving(self):
        self.calls.append(("IsMoving",))
        return int(self.moving)

    def LoadFile(self, path):
        self.calls.append(("LoadFile", path))
        self.filename = path
        self.loading = True

    def DoOEMButton(self, number):
        self.calls.append(("DoOEMButton", number))
        if number == self.fail_button:
            raise RuntimeError("Failure after command may have been received")

    def Code(self, command):
        self.calls.append(("Code", command))

    def SetUserDRO(self, code, value):
        self.calls.append(("SetUserDRO", code, value))


class FakeMach3Document:
    def __init__(self, script):
        self.script = script

    def GetScriptDispatch(self):
        return self.script


class Mach3BridgeTests(unittest.TestCase):
    def setUp(self):
        self.script = FakeMach3Script()
        self.bridge = cam.Mach3Bridge(connector=lambda: FakeMach3Document(self.script))
        self.temp = tempfile.TemporaryDirectory()
        self.path = os.path.join(self.temp.name, "fixture.nc")
        with open(self.path, "w", encoding="ascii") as stream:
            stream.write("G21 G90 G54\nM30\n")
        self.bridge.connect()

    def tearDown(self):
        self.bridge.disconnect()
        self.temp.cleanup()

    def mutations(self):
        return [c for c in self.script.calls if c[0] in ("LoadFile", "DoOEMButton", "Code", "SetUserDRO")]

    def test_attach_and_snapshot_are_read_only_and_work_dros_ignore_screen_mode(self):
        state = self.bridge.snapshot()
        self.assertEqual(state["profile"], "Mach3Mill")
        self.assertEqual(state["machine_xyz"], (100.0, 200.0, -70.0))
        self.assertEqual(state["work_xyz"], (10.0, 20.0, 6.0))
        self.assertEqual(state["homed_xyz"], (True, True, True))
        self.assertFalse(state["g92_active"])
        self.assertFalse(state["rotation_active"])
        self.assertEqual(self.mutations(), [])
        self.assertNotIn(("GetOEMDRO", 800), self.script.calls)

    def test_home_warning_is_not_inverted_into_false_homed_claim(self):
        self.script.leds[808] = 1
        self.assertEqual(self.bridge.snapshot()["homed_xyz"], (True, False, True))

    def test_load_poll_and_start_are_separate_and_start_is_single_use(self):
        self.bridge.load_file(self.path)
        self.assertFalse(self.bridge.poll_loaded())
        with self.assertRaises(cam.Mach3BridgeError):
            self.bridge.start_loaded()
        self.assertEqual(self.mutations(), [("LoadFile", self.path)])
        self.script.loading = False
        self.assertTrue(self.bridge.poll_loaded())
        self.assertEqual(self.mutations(), [("LoadFile", self.path)])
        self.bridge.start_loaded()
        self.assertEqual(self.mutations(), [("LoadFile", self.path), ("DoOEMButton", 1000)])
        with self.assertRaises(cam.Mach3BridgeError):
            self.bridge.start_loaded()
        self.assertEqual(self.mutations().count(("DoOEMButton", 1000)), 1)

    def test_different_loaded_file_cannot_start(self):
        self.bridge.load_file(self.path)
        self.script.loading = False
        self.script.filename = os.path.join(self.temp.name, "previous.nc")
        with self.assertRaises(cam.Mach3BridgeError):
            self.bridge.start_loaded()
        self.assertIsNone(self.bridge.pending_path)
        self.assertNotIn(("DoOEMButton", 1000), self.script.calls)

    def test_active_job_and_macro_do_not_get_replaced(self):
        for led in (804, 805, 806, 162):
            with self.subTest(led=led):
                self.script.leds[led] = 1
                with self.assertRaises(cam.Mach3BridgeError):
                    self.bridge.load_file(self.path)
                self.script.leds[led] = 0
        self.assertEqual(self.mutations(), [])

    def test_reset_does_not_trigger_automatic_reset_or_start(self):
        self.bridge.load_file(self.path)
        self.script.loading = False
        self.script.leds[800] = 1
        with self.assertRaises(cam.Mach3BridgeError):
            self.bridge.start_loaded()
        self.assertEqual(self.mutations(), [("LoadFile", self.path)])

    def test_uncertain_start_error_clears_intent_without_retry(self):
        self.bridge.load_file(self.path)
        self.script.loading = False
        self.script.fail_button = 1000
        with self.assertRaises(cam.Mach3BridgeError):
            self.bridge.start_loaded()
        self.assertFalse(self.bridge.connected)
        self.assertIsNone(self.bridge.pending_path)
        self.assertIn("DoOEMButton", self.bridge.last_error)
        with self.assertRaises(cam.Mach3BridgeError):
            self.bridge.start_loaded()
        self.assertEqual(self.mutations(), [("LoadFile", self.path), ("DoOEMButton", 1000)])

    def test_hold_resume_stop_send_only_documented_actions(self):
        self.bridge.hold()
        self.bridge.resume()
        self.bridge.stop()
        self.assertEqual(self.mutations(), [("DoOEMButton", 1001), ("DoOEMButton", 1005), ("DoOEMButton", 1003)])

    def test_disconnect_only_releases_client_and_cancels_pending(self):
        self.bridge.load_file(self.path)
        self.bridge.disconnect()
        self.assertIsNone(self.bridge.pending_path)
        self.assertFalse(self.bridge.connected)
        self.assertEqual(self.mutations(), [("LoadFile", self.path)])

    def test_cancel_pending_never_stops_machine(self):
        self.bridge.load_file(self.path)
        self.bridge.cancel_pending()
        self.script.loading = False
        self.assertFalse(self.bridge.poll_loaded())
        self.assertEqual(self.mutations(), [("LoadFile", self.path)])

    def test_lost_connection_does_not_return_cached_coordinates(self):
        self.script.fail_snapshot = True
        with self.assertRaises(cam.Mach3BridgeError):
            self.bridge.snapshot()
        self.assertFalse(self.bridge.connected)
        self.assertEqual(self.mutations(), [])

    def test_wrong_thread_rejected_before_com_access(self):
        results = []
        before = list(self.script.calls)
        def other_thread():
            try:
                self.bridge.snapshot()
            except cam.Mach3BridgeError as exc:
                results.append(str(exc))
        worker = threading.Thread(target=other_thread)
        worker.start()
        worker.join()
        self.assertEqual(len(results), 1)
        self.assertEqual(self.script.calls, before)

    def test_explicit_user_dro_and_macro_only_send_requested_commands(self):
        self.bridge.set_user_dro(1001, 3.25)
        self.bridge.execute_mdi("M881")
        self.assertEqual(self.mutations(), [("SetUserDRO", 1001, 3.25), ("Code", "M881")])

    def test_macro_running_prevents_overlapping_mdi_or_dro_write(self):
        self.script.leds[162] = 1
        with self.assertRaises(cam.Mach3BridgeError):
            self.bridge.execute_mdi("M881")
        with self.assertRaises(cam.Mach3BridgeError):
            self.bridge.set_user_dro(1001, 3.0)
        self.assertEqual(self.mutations(), [])

    def test_invalid_dro_or_multiline_mdi_cannot_send(self):
        for code, value in ((802, 0), (2255, 0), (1001.5, 0), (1001, float("nan")), (float("inf"), 0)):
            with self.subTest(code=code, value=value):
                with self.assertRaises(cam.Mach3BridgeError):
                    self.bridge.set_user_dro(code, value)
        for command in ("", "M881\nG0 Z0", "M881\x00"):
            with self.subTest(command=command):
                with self.assertRaises(cam.Mach3BridgeError):
                    self.bridge.execute_mdi(command)
        self.assertEqual(self.mutations(), [])


if __name__ == "__main__":
    unittest.main()
