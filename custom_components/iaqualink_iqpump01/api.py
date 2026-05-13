import threading
import logging
import json
import requests

_LOGGER = logging.getLogger(__name__)
REQUEST_TIMEOUT = 15
REDACTED = "<redacted>"
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
SENSITIVE_LOG_KEY_PARTS = (
    "credential",
    "secret",
    "session",
    "token",
)

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
    def __init__(self, email, password):
        self.email = email
        self.password = password
        self.apikey = "EOOEMOW4YR6QNB07"
        self.auth_token = None
        self.session_id = None
        self.user_id = None
        self.id_token = None
        self.serial = None
        self.data = {}
        self._refresh_lock = threading.Lock()

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
            return {
                "state": value.get("state"),
                "ssid": REDACTED,
            }
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

    def _log_response(self, label, response):
        try:
            body = self._redact_for_log(response.json())
        except ValueError:
            _LOGGER.debug(
                "[%s] Response status=%s body=<non-json, %s bytes>",
                label,
                response.status_code,
                len(response.text or ""),
            )
            return

        _LOGGER.debug(
            "[%s] Response status=%s body=%s",
            label,
            response.status_code,
            json.dumps(body, sort_keys=True),
        )

    def _raise_for_status(self, response, context):
        try:
            response.raise_for_status()
        except requests.HTTPError as err:
            status = response.status_code
            if status in (401, 403):
                raise IAqualinkAuthError(
                    f"iAquaLink authentication failed during {context}"
                ) from err
            raise IAqualinkConnectionError(
                f"iAquaLink returned HTTP {status} during {context}"
            ) from err

    def _request(self, method, url, *, check_status=True, **kwargs):
        try:
            response = requests.request(
                method, url, timeout=REQUEST_TIMEOUT, **kwargs
            )
            if check_status:
                self._raise_for_status(response, method.upper())
            return response
        except requests.Timeout:
            _LOGGER.warning(
                "[_request] iAquaLink %s request timed out after %ss: %s",
                method.upper(),
                REQUEST_TIMEOUT,
                self._safe_url(url),
            )
            raise IAqualinkConnectionError(
                f"iAquaLink {method.upper()} request timed out"
            ) from None
        except requests.HTTPError as err:
            status = err.response.status_code if err.response is not None else "unknown"
            _LOGGER.warning(
                "[_request] iAquaLink %s request returned HTTP %s: %s",
                method.upper(),
                status,
                self._safe_url(url),
            )
            if status in (401, 403):
                raise IAqualinkAuthError(
                    f"iAquaLink {method.upper()} request returned HTTP {status}"
                ) from err
            raise IAqualinkConnectionError(
                f"iAquaLink {method.upper()} request returned HTTP {status}"
            ) from err
        except requests.RequestException as err:
            _LOGGER.warning(
                "[_request] iAquaLink %s request failed for %s: %s",
                method.upper(),
                self._safe_url(url),
                err.__class__.__name__,
            )
            raise IAqualinkConnectionError(
                f"iAquaLink {method.upper()} request failed"
            ) from err

    def login(self):
        _LOGGER.debug(
            "[login] Logging in with email: %s", self._mask_email(self.email)
        )
        login_url = "https://prod.zodiac-io.com/users/v1/login"
        payload = {
            "email": self.email,
            "password": self.password,
            "apikey": self.apikey
        }
        headers = {"Content-Type": "application/json"}
        response = self._request(
            "post", login_url, json=payload, headers=headers
        )

        self._log_response("login", response)

        data = response.json()
        try:
            self.auth_token = data["authentication_token"]
            self.session_id = data["session_id"]
            self.user_id = data["id"]
            self.id_token = data["userPoolOAuth"]["IdToken"]
        except KeyError as err:
            raise IAqualinkAuthError("iAquaLink login response is missing auth data") from err

        device_url = f"https://r-api.iaqualink.net/devices.json?authentication_token={self.auth_token}&user_id={self.user_id}&api_key={self.apikey}"
        device_list = self._request("get", device_url)

        self._log_response("device_url", device_list)

        for d in device_list.json():
            if d.get("device_type") == "i2d":
                self.serial = d.get("serial_number")
                break

        if not self.serial:
            raise IAqualinkNoDeviceError(
                "No iQPump01 controller (device_type=i2d) found in this iAquaLink account"
            )

    def refresh_data(self):
        with self._refresh_lock:
            _LOGGER.debug("[refresh_data] Refreshing pump data.")
            control_url = f"https://r-api.iaqualink.net/v2/devices/{self.serial}/control.json?"
            headers = {
                "accept": "*/*",
                "content-type": "application/json",
                "cookie": f"session_id={self.session_id}; authentication_token={self.auth_token}",
                "authorization": self.id_token,
                "api_key": self.apikey,
                "user-agent": "iAqualink/934 CFNetwork/3826.500.111.2.2 Darwin/24.4.0",
                "accept-language": "fr-CA,fr;q=0.9",
                "accept-encoding": "gzip, deflate, br"
            }
            payload = {
                "user_id": str(self.user_id),
                "command": "/alldata/read"
            }

            resp = self._request(
                "post", control_url, check_status=False, headers=headers, json=payload
            )
            if resp.status_code == 401:
                _LOGGER.warning("[refresh_data] Token expired during refresh, reauthenticating...")
                self.login()
                headers["cookie"] = f"session_id={self.session_id}; authentication_token={self.auth_token}"
                headers["authorization"] = self.id_token
                resp = self._request(
                    "post",
                    control_url,
                    check_status=False,
                    headers=headers,
                    json=payload,
                )

            self._log_response("refresh_data", resp)
            self._raise_for_status(resp, "refresh_data")

            self.data = resp.json().get("alldata", {})
            return self.data

    def _send_command(self, command, param):
        control_url = f"https://r-api.iaqualink.net/v2/devices/{self.serial}/control.json?"
        headers = {
            "accept": "*/*",
            "content-type": "application/json",
            "cookie": f"session_id={self.session_id}; authentication_token={self.auth_token}",
            "authorization": self.id_token,
            "api_key": self.apikey,
            "user-agent": "iAqualink/934 CFNetwork/3826.500.111.2.2 Darwin/24.4.0",
            "accept-language": "fr-CA,fr;q=0.9",
            "accept-encoding": "gzip, deflate, br"
        }
        payload = {
            "user_id": str(self.user_id),
            "command": command,
            "params": param,
        }
        _LOGGER.debug("[_send_command] POST %s | %s", command, param)
        resp = self._request(
            "post", control_url, check_status=False, headers=headers, json=payload
        )
        if resp.status_code == 401:
            _LOGGER.warning("[_send_command] Token expired during command, reauthenticating...")
            self.login()
            headers["cookie"] = f"session_id={self.session_id}; authentication_token={self.auth_token}"
            headers["authorization"] = self.id_token
            resp = self._request(
                "post",
                control_url,
                check_status=False,
                headers=headers,
                json=payload,
            )

        _LOGGER.debug("[_send_command] Response status: %s", resp.status_code)
        self._log_response("_send_command", resp)
        self._raise_for_status(resp, command)

        data = resp.json()
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
