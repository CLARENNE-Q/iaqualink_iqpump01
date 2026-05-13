import asyncio
import json
import logging

import aiohttp

_LOGGER = logging.getLogger(__name__)
REQUEST_TIMEOUT = 15
REDACTED = "<redacted>"
CONTROL_USER_AGENT = "iAqualink/934 CFNetwork/3826.500.111.2.2 Darwin/24.4.0"
CONTROL_ACCEPT_LANGUAGE = "fr-CA,fr;q=0.9"
SENSITIVE_LOG_KEYS = {
    "accesskeyid",
    "address",
    "address_1",
    "address_2",
    "authentication_token",
    "authorization",
    "city",
    "cookie",
    "email",
    "first_name",
    "id",
    "identityid",
    "idtoken",
    "last_name",
    "password",
    "phone",
    "postal_code",
    "refreshtoken",
    "secretkey",
    "session_id",
    "sessiontoken",
    "ssid",
    "state",
    "username",
}
SENSITIVE_LOG_KEY_PARTS = ("credential", "secret", "session", "token")


class IAqualinkError(Exception):
    """Base iAquaLink API error."""


class IAqualinkAuthError(IAqualinkError):
    """Authentication or authorization failed."""


class IAqualinkConnectionError(IAqualinkError):
    """Unable to communicate with iAquaLink."""


class IAqualinkNoDeviceError(IAqualinkError):
    """No supported pump was found in the account."""


class IAqualinkCommandError(IAqualinkError):
    """iAquaLink rejected or ignored a command."""


class IAqualinkClient:
    def __init__(self, session: aiohttp.ClientSession, email, password, serial=None):
        self._session = session
        self.email = email
        self.password = password
        self.apikey = "EOOEMOW4YR6QNB07"
        self.auth_token = None
        self.session_id = None
        self.user_id = None
        self.id_token = None
        self.serial = str(serial) if serial is not None else None
        self.devices = []
        self.device = None
        self.data = {}
        self._refresh_lock = asyncio.Lock()

    @staticmethod
    def _safe_url(url):
        return url.split("?", 1)[0]

    @staticmethod
    def _mask_email(value):
        if not isinstance(value, str) or "@" not in value:
            return REDACTED
        local, domain = value.split("@", 1)
        if len(local) <= 2:
            masked_local = local[:1] + "***"
        else:
            masked_local = local[:2] + "***" + local[-1:]
        return f"{masked_local}@{domain}"

    @staticmethod
    def _mask_suffix(value, visible=4):
        text = str(value)
        if len(text) <= visible:
            return REDACTED
        return f"***{text[-visible:]}"

    @classmethod
    def _redact_value(cls, key, value):
        normalized_key = str(key).lower()
        if normalized_key == "wifistatus" and isinstance(value, dict):
            return {"state": value.get("state"), "ssid": REDACTED}
        if normalized_key == "email":
            return cls._mask_email(value)
        if normalized_key in {"serial_number", "serialnumber"}:
            return cls._mask_suffix(value)
        if normalized_key in SENSITIVE_LOG_KEYS or any(
            part in normalized_key for part in SENSITIVE_LOG_KEY_PARTS
        ):
            return REDACTED
        return cls._redact_for_log(value)

    @classmethod
    def _redact_for_log(cls, value):
        if isinstance(value, dict):
            return {key: cls._redact_value(key, item) for key, item in value.items()}
        if isinstance(value, list):
            return [cls._redact_for_log(item) for item in value]
        return value

    async def _log_response(self, label, response):
        try:
            raw_body = await response.text()
            payload = json.loads(raw_body)
            body = self._redact_for_log(payload)
        except (ValueError, aiohttp.ClientError):
            _LOGGER.debug(
                "[%s] Response status=%s body=<non-json or unreadable>",
                label,
                response.status,
            )
            return

        _LOGGER.debug(
            "[%s] Response status=%s body=%s",
            label,
            response.status,
            json.dumps(body, sort_keys=True),
        )

    def _raise_for_status(self, status, context):
        if 200 <= status < 300:
            return
        if status in (401, 403):
            raise IAqualinkAuthError(f"iAquaLink authentication failed during {context}")
        raise IAqualinkConnectionError(f"iAquaLink returned HTTP {status} during {context}")

    async def _request(self, method, url, *, check_status=True, context=None, **kwargs):
        timeout = aiohttp.ClientTimeout(total=REQUEST_TIMEOUT)
        try:
            response = await self._session.request(method, url, timeout=timeout, **kwargs)
        except asyncio.TimeoutError:
            _LOGGER.warning(
                "[_request] iAquaLink %s request timed out after %ss: %s",
                method.upper(),
                REQUEST_TIMEOUT,
                self._safe_url(url),
            )
            raise IAqualinkConnectionError(
                f"iAquaLink {method.upper()} request timed out"
            ) from None
        except aiohttp.ClientError as err:
            _LOGGER.warning(
                "[_request] iAquaLink %s request failed for %s: %s",
                method.upper(),
                self._safe_url(url),
                err.__class__.__name__,
            )
            raise IAqualinkConnectionError(
                f"iAquaLink {method.upper()} request failed"
            ) from err

        if check_status:
            self._raise_for_status(response.status, context or method.upper())
        return response

    async def _parse_json(self, response, context):
        try:
            return await response.json(content_type=None)
        except (ValueError, aiohttp.ContentTypeError) as err:
            raise IAqualinkConnectionError(
                f"iAquaLink returned invalid JSON during {context}"
            ) from err

    def _control_url(self):
        return f"https://r-api.iaqualink.net/v2/devices/{self.serial}/control.json?"

    def _control_headers(self):
        return {
            "accept": "*/*",
            "content-type": "application/json",
            "cookie": f"session_id={self.session_id}; authentication_token={self.auth_token}",
            "authorization": self.id_token,
            "api_key": self.apikey,
            "user-agent": CONTROL_USER_AGENT,
            "accept-language": CONTROL_ACCEPT_LANGUAGE,
            "accept-encoding": "gzip, deflate, br",
        }

    async def _post_control(self, payload, context):
        control_url = self._control_url()
        headers = self._control_headers()
        response = await self._request(
            "post",
            control_url,
            check_status=False,
            context=context,
            headers=headers,
            json=payload,
        )
        if response.status == 401:
            _LOGGER.warning("[%s] Token expired, reauthenticating...", context)
            await self.login()
            headers = self._control_headers()
            response = await self._request(
                "post",
                control_url,
                check_status=False,
                context=context,
                headers=headers,
                json=payload,
            )
        return response

    async def login(self):
        _LOGGER.debug("[login] Logging in with email: %s", self._mask_email(self.email))
        login_url = "https://prod.zodiac-io.com/users/v1/login"
        payload = {"email": self.email, "password": self.password, "apikey": self.apikey}
        headers = {"Content-Type": "application/json"}
        response = await self._request(
            "post", login_url, context="login", json=payload, headers=headers
        )

        await self._log_response("login", response)
        data = await self._parse_json(response, "login")
        try:
            self.auth_token = data["authentication_token"]
            self.session_id = data["session_id"]
            self.user_id = data["id"]
            self.id_token = data["userPoolOAuth"]["IdToken"]
        except KeyError as err:
            raise IAqualinkAuthError("iAquaLink login response is missing auth data") from err

        device_url = (
            "https://r-api.iaqualink.net/devices.json"
            f"?authentication_token={self.auth_token}&user_id={self.user_id}&api_key={self.apikey}"
        )
        device_list = await self._request("get", device_url, context="devices list")

        await self._log_response("device_url", device_list)
        devices_payload = await self._parse_json(device_list, "devices list")
        if isinstance(devices_payload, dict):
            devices_payload = devices_payload.get("devices", [])

        self.devices = [
            device
            for device in devices_payload
            if (
                isinstance(device, dict)
                and device.get("device_type") == "i2d"
                and device.get("serial_number")
            )
        ]

        if not self.devices:
            raise IAqualinkNoDeviceError(
                "No iQPump01 controller (device_type=i2d) found in this iAquaLink account"
            )

        if self.serial:
            self.device = next(
                (
                    device
                    for device in self.devices
                    if device.get("serial_number") == self.serial
                ),
                None,
            )
            if self.device is None:
                raise IAqualinkNoDeviceError(
                    f"Configured iQPump01 controller {self._mask_suffix(self.serial)} "
                    "was not found in this iAquaLink account"
                )
            return

        self.device = self.devices[0]
        self.serial = self.device.get("serial_number")

    async def refresh_data(self):
        async with self._refresh_lock:
            _LOGGER.debug("[refresh_data] Refreshing pump data.")
            payload = {"user_id": str(self.user_id), "command": "/alldata/read"}

            resp = await self._post_control(payload, "refresh_data")

            await self._log_response("refresh_data", resp)
            self._raise_for_status(resp.status, "refresh_data")

            response_data = await self._parse_json(resp, "refresh_data")
            self.data = response_data.get("alldata", {})
            return self.data

    async def _send_command(self, command, param):
        payload = {
            "user_id": str(self.user_id),
            "command": command,
            "params": param,
        }
        _LOGGER.debug("[_send_command] POST %s | %s", command, param)
        resp = await self._post_control(payload, "_send_command")

        _LOGGER.debug("[_send_command] Response status: %s", resp.status)
        await self._log_response("_send_command", resp)
        self._raise_for_status(resp.status, command)

        data = await self._parse_json(resp, "_send_command")
        command_key = command.strip("/").split("/")[0]
        expected_value = param.removeprefix("value=") if param.startswith("value=") else None
        returned_value = data.get(command_key, {}).get("value")
        if (
            expected_value is not None
            and returned_value is not None
            and str(returned_value) != str(expected_value)
        ):
            raise IAqualinkCommandError(
                f"iAquaLink returned {command_key}={returned_value} "
                f"after requested {command_key}={expected_value}"
            )
        return data
