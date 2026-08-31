import json
import sys
import tempfile
import unittest
from pathlib import Path


SOURCE_DIR = Path(__file__).resolve().parents[1]
if not (SOURCE_DIR / "cfrp_router_cam.py").is_file():
    SOURCE_DIR = SOURCE_DIR / "CFRP_Router_CAM_V1.10_source"
sys.path.insert(0, str(SOURCE_DIR))

import cfrp_router_cam as cam


class FakeVar:
    def __init__(self, value=None):
        self.value = value

    def get(self):
        return self.value

    def set(self, value):
        self.value = value


class FakeText:
    def __init__(self, value=""):
        self.value = value

    def get(self, _start, _end):
        return self.value

    def delete(self, _start, _end):
        self.value = ""

    def insert(self, _start, value):
        self.value = value


class SettingsHarness:
    settings_path = cam.App.settings_path
    load_settings = cam.App.load_settings
    save_settings = cam.App.save_settings
    write_settings_file = cam.App.write_settings_file

    def __init__(self, portable_dir, appdata_path):
        self._portable_dir = str(portable_dir)
        self._appdata_path = str(appdata_path)
        self.vars = {"machine_home_enabled": FakeVar(False)}
        self.font_size_var = FakeVar(10)
        self.start_text = FakeText(cam.DEFAULT_START_CODE)
        self.end_text = FakeText(cam.DEFAULT_END_CODE)
        self.status = FakeVar("")

    def executable_dir(self):
        return self._portable_dir

    def portable_settings_path(self):
        return str(Path(self._portable_dir) / cam.SETTINGS_FILENAME)

    def appdata_settings_path(self):
        return self._appdata_path

    def apply_font_size(self, silent=True):
        del silent


class PortableSettingsTests(unittest.TestCase):
    def test_portable_file_is_preferred(self):
        with tempfile.TemporaryDirectory() as root:
            root = Path(root)
            portable = root / "portable" / "settings.json"
            legacy = root / "appdata" / "settings.json"
            portable.parent.mkdir()
            legacy.parent.mkdir()
            portable.write_text("{}", encoding="utf-8")
            legacy.write_text("{}", encoding="utf-8")
            app = SettingsHarness(portable.parent, legacy)
            self.assertEqual(Path(app.settings_path()), portable)

    def test_existing_appdata_settings_migrate_next_to_exe(self):
        with tempfile.TemporaryDirectory() as root:
            root = Path(root)
            portable_dir = root / "portable"
            portable_dir.mkdir()
            legacy = root / "appdata" / "settings.json"
            legacy.parent.mkdir()
            legacy.write_text(
                json.dumps(
                    {
                        "version": "1.03",
                        "vars": {"machine_home_enabled": True},
                        "font_size": 11,
                        "start_code": cam.V103_DEFAULT_START_CODE,
                        "end_code": cam.DEFAULT_END_CODE,
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )

            app = SettingsHarness(portable_dir, legacy)
            app.load_settings()

            portable = portable_dir / "settings.json"
            self.assertTrue(portable.is_file())
            migrated = json.loads(portable.read_text(encoding="utf-8"))
            self.assertEqual(migrated["version"], cam.APP_VERSION)
            self.assertNotIn("G92.1", migrated["start_code"])
            self.assertTrue(migrated["vars"]["machine_home_enabled"])
            self.assertEqual(migrated["font_size"], 11)

    def test_first_save_creates_file_next_to_exe(self):
        with tempfile.TemporaryDirectory() as root:
            root = Path(root)
            portable_dir = root / "portable"
            portable_dir.mkdir()
            legacy = root / "appdata" / "settings.json"
            app = SettingsHarness(portable_dir, legacy)

            app.save_settings()

            saved = json.loads(
                (portable_dir / "settings.json").read_text(encoding="utf-8")
            )
            self.assertEqual(saved["version"], cam.APP_VERSION)
            self.assertNotIn("G92.1", saved["start_code"])

    def test_read_only_exe_folder_falls_back_to_appdata(self):
        with tempfile.TemporaryDirectory() as root:
            root = Path(root)
            portable_dir = root / "portable"
            portable_dir.mkdir()
            legacy = root / "appdata" / "settings.json"
            app = SettingsHarness(portable_dir, legacy)
            portable = str(portable_dir / "settings.json")
            write_file = app.write_settings_file

            def fail_portable_write(path, data):
                if path == portable:
                    raise OSError("simulated read-only executable folder")
                write_file(path, data)

            app.write_settings_file = fail_portable_write
            app.save_settings()

            saved = json.loads(legacy.read_text(encoding="utf-8"))
            self.assertEqual(saved["version"], cam.APP_VERSION)
            self.assertFalse((portable_dir / "settings.json").exists())


if __name__ == "__main__":
    unittest.main()
