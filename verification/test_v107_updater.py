import hashlib
import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "cfrp_router_cam.py"
if not SOURCE.is_file():
    SOURCE = ROOT / "CFRP_Router_CAM_V1.10_source" / "cfrp_router_cam.py"
SPEC = importlib.util.spec_from_file_location("carbon_cam_updater_v110", SOURCE)
cam = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = cam
SPEC.loader.exec_module(cam)


class UpdaterTests(unittest.TestCase):
    def test_version_comparison(self):
        self.assertTrue(cam.newer_version("1.8", "1.07"))
        self.assertTrue(cam.newer_version("2.0.1", "2.0"))
        self.assertFalse(cam.newer_version("1.07", "1.7.0"))
        self.assertFalse(cam.newer_version("1.06", "1.07"))

    def test_manifest_accepts_only_newer_github_release(self):
        data = {
            "version": "1.12",
            "download_url": cam.UPDATE_DOWNLOAD_PREFIX + "v1.12/CFRP_Router_CAM.exe",
            "sha256": "a" * 64,
            "message": "test",
        }
        self.assertEqual(cam.validated_update_manifest(data)["version"], "1.12")
        data["version"] = cam.APP_VERSION
        self.assertIsNone(cam.validated_update_manifest(data))
        data["version"] = "1.12"
        data["download_url"] = "https://example.com/update.exe"
        with self.assertRaises(ValueError):
            cam.validated_update_manifest(data)

    def test_verified_executable_replaces_old_file(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            source = root / cam.UPDATE_TEMP_FILENAME
            target = root / "CFRP_Router_CAM.exe"
            source.write_bytes(b"new executable")
            target.write_bytes(b"old executable")
            expected = hashlib.sha256(source.read_bytes()).hexdigest()

            cam.replace_executable_files(str(source), str(target), expected)

            self.assertEqual(target.read_bytes(), b"new executable")
            self.assertTrue(source.exists())
            self.assertFalse(Path(str(target) + ".update-backup").exists())

    def test_failed_copy_restores_old_executable(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            source = root / cam.UPDATE_TEMP_FILENAME
            target = root / "CFRP_Router_CAM.exe"
            source.write_bytes(b"new executable")
            target.write_bytes(b"old executable")
            expected = hashlib.sha256(source.read_bytes()).hexdigest()

            with mock.patch.object(cam.shutil, "copy2", side_effect=OSError("copy failed")):
                with self.assertRaises(OSError):
                    cam.replace_executable_files(str(source), str(target), expected)

            self.assertEqual(target.read_bytes(), b"old executable")


if __name__ == "__main__":
    unittest.main()
