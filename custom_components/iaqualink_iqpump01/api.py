import time
import threading
import logging
import requests

_LOGGER = logging.getLogger(__name__)

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

    def login(self):
        _LOGGER.debug("[login] Logging in with email: %s", self.email)
        login_url = "https://prod.zodiac-io.com/users/v1/login"
        payload = {
            "email": self.email,
            "password": self.password,
            "apikey": self.apikey
        }
        headers = {"Content-Type": "application/json"}
        response = requests.post(login_url, json=payload, headers=headers)

        _LOGGER.debug("[login] Response: %s", response.text)

        if response.status_code != 200:
            raise Exception("Login failed")

        data = response.json()
        self.auth_token = data["authentication_token"]
        self.session_id = data["session_id"]
        self.user_id = data["id"]
        self.id_token = data["userPoolOAuth"]["IdToken"]

        device_url = f"https://r-api.iaqualink.net/devices.json?authentication_token={self.auth_token}&user_id={self.user_id}&api_key={self.apikey}"
        device_list = requests.get(device_url)

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
            resp = requests.post(control_url, headers=headers, json=payload)
            _LOGGER.debug("[refresh_data] Response: %s", resp.text)

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
        resp = requests.post(control_url, headers=headers, json=payload)
        _LOGGER.debug("[_send_command] Response: %s", resp.text)
        return resp
