"""The watchdog must capture a blocked UI thread without leaking job paths."""
import tempfile
import time
import unittest
from pathlib import Path

import cfrp_router_cam as cam


class UiDiagnosticsTests(unittest.TestCase):
    def test_stall_and_recovery_record_action_and_sanitized_stack(self):
        with tempfile.TemporaryDirectory() as temp:
            diagnostic = cam.UiDiagnostics(temp, stall_seconds=0.04, poll_seconds=0.005)
            try:
                diagnostic.heartbeat()
                with diagnostic.activity("test_import", contours=27, objects=3):
                    time.sleep(0.12)  # The Tk thread is unable to service its heartbeat.
                diagnostic.heartbeat()
                log = Path(diagnostic.path).read_text(encoding="utf-8")
                self.assertIn("ui_unresponsive", log)
                self.assertIn("ui_recovered", log)
                self.assertIn("action=test_import", log)
                self.assertIn("contours=27", log)
                self.assertIn("objects=3", log)
                self.assertNotIn(temp, log)
            finally:
                diagnostic.close()

    def test_brief_action_does_not_report_stall_and_close_stops_watcher(self):
        with tempfile.TemporaryDirectory() as temp:
            diagnostic = cam.UiDiagnostics(temp, stall_seconds=0.5, poll_seconds=0.01)
            diagnostic.heartbeat()
            with diagnostic.activity("test_redraw"):
                pass
            diagnostic.close()
            diagnostic.close()
            log = Path(diagnostic.path).read_text(encoding="utf-8")
            self.assertNotIn("ui_unresponsive", log)
            self.assertEqual(log.count("session_end"), 1)

    def test_error_message_and_private_path_are_not_recorded(self):
        with tempfile.TemporaryDirectory() as temp:
            diagnostic = cam.UiDiagnostics(temp, stall_seconds=1)
            try:
                try:
                    raise ValueError(str(Path(temp) / "private_customer_part.dxf"))
                except ValueError as exc:
                    diagnostic.error("open_dxf", exc)
                log = Path(diagnostic.path).read_text(encoding="utf-8")
                self.assertIn("error=ValueError", log)
                self.assertNotIn("private_customer_part", log)
                self.assertNotIn(temp, log)
            finally:
                diagnostic.close()

    def test_log_rotates_at_size_limit(self):
        with tempfile.TemporaryDirectory() as temp:
            diagnostic = cam.UiDiagnostics(temp, stall_seconds=1)
            try:
                Path(diagnostic.path).write_text("x" * 2_000_001, encoding="utf-8")
                diagnostic.write("rotation_check")
                self.assertTrue(Path(diagnostic.path + ".1").is_file())
                self.assertIn("rotation_check", Path(diagnostic.path).read_text(encoding="utf-8"))
            finally:
                diagnostic.close()

    def test_waiting_in_operator_dialog_is_not_reported_as_hang(self):
        with tempfile.TemporaryDirectory() as temp:
            diagnostic = cam.UiDiagnostics(temp, stall_seconds=0.04, poll_seconds=0.005)
            try:
                diagnostic.heartbeat()
                dialog_wait = compile("time.sleep(0.12)", "messagebox.py", "exec")
                exec(dialog_wait, {"time": time})
                diagnostic.heartbeat()
                log = Path(diagnostic.path).read_text(encoding="utf-8")
                self.assertNotIn("ui_unresponsive", log)
            finally:
                diagnostic.close()
