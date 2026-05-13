import importlib.util
import json
import pathlib
import unittest
import sys
import types

aiohttp_stub = types.ModuleType("aiohttp")
aiohttp_stub.ClientSession = object
aiohttp_stub.ClientError = Exception
aiohttp_stub.ContentTypeError = ValueError
aiohttp_stub.ClientTimeout = lambda total=None: {"total": total}
sys.modules.setdefault("aiohttp", aiohttp_stub)


MODULE_PATH = pathlib.Path(__file__).resolve().parents[1] / "custom_components/iaqualink_iqpump01/api.py"
spec = importlib.util.spec_from_file_location("iaqualink_api", MODULE_PATH)
api = importlib.util.module_from_spec(spec)
spec.loader.exec_module(api)


class _DummySession:
    async def request(self, *args, **kwargs):
        raise RuntimeError("not used in these unit tests")


class _FakeResponse:
    def __init__(self, payload=None, text_data="", raise_json=False):
        self._payload = payload
        self._text_data = text_data
        self._raise_json = raise_json
        self.status = 200

    async def text(self):
        return self._text_data

    async def json(self, content_type=None):
        if self._raise_json:
            raise ValueError("invalid json")
        return self._payload


class TestApiHelpers(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.client = api.IAqualinkClient(_DummySession(), "john.doe@example.com", "pwd", "123456")

    def test_redact_for_log_masks_sensitive_values(self):
        payload = {
            "email": "john.doe@example.com",
            "session_id": "ABC123",
            "serial_number": "SN123456789",
            "wifistatus": {"state": "connected", "ssid": "MyWifi"},
        }
        redacted = self.client._redact_for_log(payload)
        self.assertEqual(redacted["session_id"], api.REDACTED)
        self.assertEqual(redacted["wifistatus"]["ssid"], api.REDACTED)
        self.assertTrue(redacted["email"].endswith("@example.com"))
        self.assertTrue(redacted["serial_number"].startswith("***"))

    async def test_parse_json_success(self):
        response = _FakeResponse(payload={"ok": True})
        result = await self.client._parse_json(response, "test")
        self.assertEqual(result, {"ok": True})

    async def test_parse_json_failure_raises_domain_error(self):
        response = _FakeResponse(raise_json=True)
        with self.assertRaises(api.IAqualinkConnectionError):
            await self.client._parse_json(response, "test")

    async def test_log_response_handles_non_json_text(self):
        response = _FakeResponse(text_data="not-json")
        await self.client._log_response("test", response)

    async def test_log_response_handles_json_text(self):
        response = _FakeResponse(text_data=json.dumps({"session_id": "SECRET"}))
        await self.client._log_response("test", response)


if __name__ == "__main__":
    unittest.main()
