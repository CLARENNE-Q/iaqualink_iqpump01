import importlib.util
import pathlib
import unittest

MODULE_PATH = pathlib.Path(__file__).resolve().parents[1] / "custom_components/iaqualink_iqpump01/const.py"
spec = importlib.util.spec_from_file_location("iaqualink_const", MODULE_PATH)
const = importlib.util.module_from_spec(spec)
spec.loader.exec_module(const)


class TestOptionInt(unittest.TestCase):
    def test_returns_value_when_int(self):
        self.assertEqual(const.option_int({"x": 42}, "x", 1), 42)

    def test_casts_string_value(self):
        self.assertEqual(const.option_int({"x": "42"}, "x", 1), 42)

    def test_returns_default_for_invalid(self):
        self.assertEqual(const.option_int({"x": "bad"}, "x", 7), 7)

    def test_returns_default_when_missing(self):
        self.assertEqual(const.option_int({}, "x", 7), 7)


if __name__ == "__main__":
    unittest.main()
