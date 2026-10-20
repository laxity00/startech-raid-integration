"""Authenticated internal cached API client. Never issues hardware commands."""
import ipaddress
import json
import re
import aiohttp
from .model import validate


class InvalidAuth(Exception):
    """Invalid private app credential."""


def base_url(host, port):
    if not isinstance(host, str) or type(port) is not int or not 1 <= port <= 65535:
        raise ValueError("Invalid host or port")
    try:
        address = ipaddress.ip_address(host)
    except ValueError:
        if not re.fullmatch(r"[A-Za-z0-9](?:[A-Za-z0-9.-]{0,251}[A-Za-z0-9])?", host):
            raise ValueError("Enter a hostname only, without scheme, credentials or path") from None
    else:
        if address.version == 6:
            host = f"[{host}]"
    return f"http://{host}:{port}"


class Client:
    def __init__(self, session, host, port, token):
        self.session, self.url = session, base_url(host, port)
        if not isinstance(token, str) or not re.fullmatch(r"[0-9a-f]{64}", token):
            raise ValueError("Expected the 64-character token shown on the app Configuration page")
        self.token = token

    async def status(self):
        async with self.session.get(self.url + "/v1/status", headers={"Authorization": "Bearer " + self.token}, timeout=aiohttp.ClientTimeout(total=10), allow_redirects=False) as response:
            if response.status in (401, 403):
                raise InvalidAuth("App token rejected")
            if response.status != 200:
                raise ValueError("App API did not return success")
            body = bytearray()
            while True:
                chunk = await response.content.read(8192)
                if not chunk:
                    break
                body.extend(chunk)
                if len(body) > 131072:
                    raise ValueError("App API response too large")
            return validate(json.loads(body))
