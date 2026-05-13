import time
import threading
import logging
import requests

_LOGGER = logging.getLogger(__name__)
REQUEST_TIMEOUT = 15

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
        self.last_refresh = 0
        self._refresh_lock = threading.Lock()

    @staticmethod
    def _safe_url(url):
        return url.split("?", 1)[0]

    def _request(self, method, url, *, check_status=True, **kwargs):
        try:
            response = requests.request(
                method, url, timeout=REQUEST_TIMEOUT, **kwargs
            )
            if check_status:
                response.raise_for_status()
            return response
        except requests.Timeout:
            _LOGGER.warning(
                "[_request] iAquaLink %s request timed out after %ss: %s",
                method.upper(),
                REQUEST_TIMEOUT,
                self._safe_url(url),
            )
            raise
        except requests.HTTPError as err:
            status = err.response.status_code if err.response is not None else "unknown"
            _LOGGER.warning(
                "[_request] iAquaLink %s request returned HTTP %s: %s",
                method.upper(),
                status,
                self._safe_url(url),
            )
            raise
        except requests.RequestException as err:
            _LOGGER.warning(
                "[_request] iAquaLink %s request failed for %s: %s",
                method.upper(),
                self._safe_url(url),
                err.__class__.__name__,
            )
            raise

    def login(self):
        _LOGGER.debug("[login] Logging in with email: %s", self.email)
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

        _LOGGER.debug("[login] Response: %s", response.text)

        data = response.json()
        self.auth_token = data["authentication_token"]
        self.session_id = data["session_id"]
        self.user_id = data["id"]
        self.id_token = data["userPoolOAuth"]["IdToken"]

        device_url = f"https://r-api.iaqualink.net/devices.json?authentication_token={self.auth_token}&user_id={self.user_id}&api_key={self.apikey}"
        device_list = self._request("get", device_url)

        _LOGGER.debug("[device_url] Response: %s", device_list.text)

        for d in device_list.json():
            if d.get("device_type") == "i2d":
                self.serial = d.get("serial_number")
                break

        if not self.serial:
            _LOGGER.error("[login] No iQPump01 controller (device_type=i2d) found in your account. Make sure the pump is linked to your iAquaLink account.")

    def refresh_data(self):
        with self._refresh_lock:
            now = time.time()
            if self.last_refresh and now - self.last_refresh < 60:
                _LOGGER.debug("[refresh_data] Using cached pump data.")
                return self.data

            _LOGGER.debug("[refresh_data] Refreshing pump data...")
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

            _LOGGER.debug("[refresh_data] Response: %s", resp.text)
            resp.raise_for_status()

            self.data = resp.json().get("alldata", {})
            self.last_refresh = now
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
        _LOGGER.debug("[_send_command] Response body: %s", resp.text)
        resp.raise_for_status()

        data = resp.json()
        command_key = command.strip("/").split("/")[0]
        expected_value = param.removeprefix("value=") if param.startswith("value=") else None
        returned_value = data.get(command_key, {}).get("value")
        if (
            expected_value is not None
            and returned_value is not None
            and str(returned_value) != str(expected_value)
        ):
            _LOGGER.warning(
                "[_send_command] iAquaLink returned %s=%s after requested %s=%s",
                command_key,
                returned_value,
                command_key,
                expected_value,
            )
        return data
