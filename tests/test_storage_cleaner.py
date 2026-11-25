"""Unit tests for cache_cleaner.py and goinfre.py."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from cache_cleaner import CacheCleaner, dir_size, format_size
import goinfre


class TestStorageCleaner(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.home = Path(self.temp_dir.name)
        self.cleaner = CacheCleaner(home=self.home, root=self.home)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_format_size(self):
        self.assertEqual(format_size(500 * 1024), "500.0 KiB")
        self.assertEqual(format_size(15 * 1024 * 1024), "15.0 MiB")
        self.assertEqual(format_size(2 * 1024 * 1024 * 1024), "2.00 GiB")

    def test_scan_and_clean_allowlisted_cache(self):
        test_cache = self.home / ".config/Code/Cache"
        test_cache.mkdir(parents=True, exist_ok=True)
        sample_file = test_cache / "data.bin"
        sample_file.write_bytes(b"A" * 1024 * 100)

        with patch("cache_cleaner.get_running_processes", return_value=set()):
            items = self.cleaner.scan()
            matched = [item for item in items if item["relative"] == ".config/Code/Cache"]
            self.assertEqual(len(matched), 1)
            self.assertTrue(matched[0]["eligible"])

            cleaned_bytes, log = self.cleaner.clean([str(test_cache)])
            self.assertGreater(cleaned_bytes, 0)
            self.assertTrue(test_cache.is_dir())
            self.assertFalse(sample_file.exists())

    def test_running_app_cache_is_skipped(self):
        test_cache = self.home / ".config/Code/Cache"
        test_cache.mkdir(parents=True, exist_ok=True)
        sample_file = test_cache / "active.bin"
        sample_file.write_bytes(b"data")

        with patch("cache_cleaner.get_running_processes", return_value={"code"}):
            items = self.cleaner.scan()
            matched = [item for item in items if item["relative"] == ".config/Code/Cache"]
            if matched:
                self.assertFalse(matched[0]["eligible"])

            cleaned_bytes, log = self.cleaner.clean([str(test_cache)])
            self.assertEqual(cleaned_bytes, 0)
            self.assertTrue(sample_file.exists())

    def test_goinfre_relocation_and_restoration(self):
        src = self.home / "heavy_folder"
        src.mkdir()
        (src / "file.dat").write_text("hello goinfre")
        target_base = self.home / "goinfre_dest"
        target_base.mkdir()

        ok, msg = goinfre.relocate_directory(src, target_base)
        self.assertTrue(ok)
        self.assertTrue(src.is_symlink())
        self.assertTrue((src / "file.dat").exists())

        ok_rest, msg_rest = goinfre.restore_directory(src)
        self.assertTrue(ok_rest)
        self.assertFalse(src.is_symlink())
        self.assertTrue((src / "file.dat").exists())


if __name__ == "__main__":
    unittest.main()
