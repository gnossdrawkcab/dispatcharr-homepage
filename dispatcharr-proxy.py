import base64
import json
import os
import threading
import time
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib import error, request

BASE_URL = os.getenv("DISPATCHARR_BASE_URL", "").rstrip("/")
STATUS_PATH = os.getenv("DISPATCHARR_STATUS_PATH", "/proxy/ts/status")
TOKEN_PATH = os.getenv("DISPATCHARR_TOKEN_PATH", "/api/accounts/token/")
REFRESH_PATH = os.getenv("DISPATCHARR_REFRESH_PATH", "/api/accounts/token/refresh/")
USERNAME = os.getenv("DISPATCHARR_USERNAME")
PASSWORD = os.getenv("DISPATCHARR_PASSWORD")
HOST = os.getenv("DISPATCHARR_PROXY_HOST", "0.0.0.0")
PORT = int(os.getenv("DISPATCHARR_PROXY_PORT", "8080"))

_token_lock = threading.Lock()
_access_token = None
_refresh_token = None
_access_exp = 0


def _decode_jwt_exp(token):
	try:
		parts = token.split(".")
		if len(parts) < 2:
			return 0
		payload = parts[1]
		padding = "=" * (-len(payload) % 4)
		data = base64.urlsafe_b64decode(payload + padding).decode("utf-8")
		return int(json.loads(data).get("exp", 0))
	except Exception:
		return 0


def _token_valid():
	return _access_token and (_access_exp - 30) > time.time()


def _set_tokens(access, refresh=None):
	global _access_token, _refresh_token, _access_exp
	_access_token = access
	if refresh:
		_refresh_token = refresh
	_access_exp = _decode_jwt_exp(access)


def _request(url, method="GET", headers=None, body=None):
	req = request.Request(url, method=method, headers=headers or {}, data=body)
	try:
		with request.urlopen(req, timeout=10) as resp:
			return resp.status, resp.read()
	except error.HTTPError as exc:
		return exc.code, exc.read()


def _login():
	if not USERNAME or not PASSWORD:
		raise RuntimeError("Missing DISPATCHARR_USERNAME or DISPATCHARR_PASSWORD")

	body = json.dumps({"username": USERNAME, "password": PASSWORD}).encode("utf-8")
	headers = {"Content-Type": "application/json", "Accept": "application/json"}
	status, data = _request(f"{BASE_URL}{TOKEN_PATH}", method="POST", headers=headers, body=body)
	if status >= 400:
		raise RuntimeError(f"Login failed with status {status}")

	payload = json.loads(data.decode("utf-8"))
	access = payload.get("access")
	refresh = payload.get("refresh")
	if not access:
		raise RuntimeError("Login response missing access token")
	_set_tokens(access, refresh)


def _refresh():
	if not _refresh_token:
		return False
	body = json.dumps({"refresh": _refresh_token}).encode("utf-8")
	headers = {"Content-Type": "application/json", "Accept": "application/json"}
	status, data = _request(f"{BASE_URL}{REFRESH_PATH}", method="POST", headers=headers, body=body)
	if status >= 400:
		return False
	payload = json.loads(data.decode("utf-8"))
	access = payload.get("access")
	if not access:
		return False
	_set_tokens(access, _refresh_token)
	return True


class DispatcharrProxyHandler(BaseHTTPRequestHandler):
	def do_GET(self):
		if self.path == "/health":
			self._send_json(200, {"status": "ok"})
			return
		if self.path != "/status":
			self._send_json(404, {"error": "not_found"})
			return
		if not BASE_URL:
			self._send_json(500, {"error": "missing_base_url"})
			return

		with _token_lock:
			if not _token_valid():
				if not _refresh():
					_login()

		headers = {"Accept": "application/json", "Authorization": f"Bearer {_access_token}"}
		status, data = _request(f"{BASE_URL}{STATUS_PATH}", headers=headers)
		if status == 401:
			with _token_lock:
				_login()
			headers["Authorization"] = f"Bearer {_access_token}"
			status, data = _request(f"{BASE_URL}{STATUS_PATH}", headers=headers)

		self.send_response(status)
		self.send_header("Content-Type", "application/json")
		self.end_headers()
		self.wfile.write(data)

	def log_message(self, format, *args):
		return

	def _send_json(self, status, payload):
		self.send_response(status)
		self.send_header("Content-Type", "application/json")
		self.end_headers()
		self.wfile.write(json.dumps(payload).encode("utf-8"))


if __name__ == "__main__":
	server = HTTPServer((HOST, PORT), DispatcharrProxyHandler)
	server.serve_forever()
