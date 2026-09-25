"""Wheel tag matching for the first-run Paddle install. No network."""
import importlib
import sys
import unittest

from packaging.tags import Tag

import core.paddle_bootstrap as pb


class WheelCompatTests(unittest.TestCase):
    def setUp(self):
        self._saved = pb._COMPAT_TAGS
        pb._COMPAT_TAGS = {
            Tag("cp312", "cp312", "win_amd64"),
            Tag("cp312", "none", "win_amd64"),
            Tag("cp312", "abi3", "win_amd64"),
            Tag("cp310", "abi3", "win_amd64"),
            Tag("cp38", "abi3", "win_amd64"),
            Tag("py3", "none", "any"),
        }

    def tearDown(self):
        pb._COMPAT_TAGS = self._saved

    def test_abi3_minimum_tag_matches_newer_cpython(self):
        self.assertTrue(pb._compat("safetensors-0.6.2-cp38-abi3-win_amd64.whl"))
        self.assertTrue(pb._compat("safetensors-0.8.0-cp310-abi3-win_amd64.whl"))

    def test_exact_cpython_wheel(self):
        self.assertTrue(pb._compat("paddlepaddle-3.3.0-cp312-cp312-win_amd64.whl"))

    def test_rejects_other_platform_and_newer_python(self):
        self.assertFalse(pb._compat("safetensors-0.6.2-cp38-abi3-win32.whl"))
        self.assertFalse(pb._compat("safetensors-0.9.0-cp314-cp314-win_amd64.whl"))
        self.assertFalse(pb._compat("not-a-wheel.txt"))


class SetuptoolsStubTests(unittest.TestCase):
    def test_missing_easy_install_is_stubbed(self):
        name = "setuptools.command.easy_install"
        saved = sys.modules.get(name)
        sys.modules.pop(name, None)

        class _Block:
            def find_spec(self, fullname, path, target=None):
                if fullname == name:
                    raise ModuleNotFoundError(name)
                return None

        blocker = _Block()
        sys.meta_path.insert(0, blocker)
        try:
            pb._stub_removed_setuptools()
            mod = importlib.import_module(name)
            self.assertTrue(isinstance(mod.easy_install, type))
        finally:
            sys.meta_path.remove(blocker)
            if saved is not None:
                sys.modules[name] = saved
            else:
                sys.modules.pop(name, None)
            parent = sys.modules.get("setuptools.command")
            if parent is not None and saved is not None:
                parent.easy_install = saved
