#!/usr/bin/env python3
"""Minimal Chrome DevTools Protocol (CDP) client — Python stdlib only.

Targets an already-running Chromium-family browser (Chrome / Edge / Brave…)
started with ``--remote-debugging-port`` (see ``bin/edge-cdp.*`` for a
Windows / POSIX launcher). No third-party dependencies: speaks HTTP for
target discovery and a hand-rolled RFC 6455 WebSocket for RPC.

Usage as a library::

    from x_cdp import CDPSession, discover, pick_page

    targets = discover("http://127.0.0.1:9222")
    target = pick_page(targets, "x.com")
    with CDPSession(target["webSocketDebuggerUrl"]) as cdp:
        value = cdp.evaluate("location.href")

Usage as a CLI::

    python src/x_cdp.py list                       # list open pages
    python src/x_cdp.py eval "document.title"      # evaluate on first page
    python src/x_cdp.py eval "document.title" --match x.com
    python src/x_cdp.py nav https://example.com --match x.com
"""

from __future__ import annotations

import argparse
import json
import os
import socket
import struct
import sys
import time
import urllib.parse
import urllib.request
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Iterable

DEFAULT_BASE = "http://127.0.0.1:9222"
FRAME_MAX = 4 * 1024 * 1024  # safety cap for a single WS payload


# ─── HTTP target discovery ────────────────────────────────────────────────


def _http_json(url: str, method: str = "GET", timeout: float = 5.0) -> Any:
    """Fetch a CDP HTTP endpoint and decode JSON (shape varies per endpoint)."""
    req = urllib.request.Request(url, method=method)
    with urllib.request.urlopen(req, timeout=timeout) as resp:  # noqa: S310
        return json.loads(resp.read().decode("utf-8"))


def discover(base: str = DEFAULT_BASE, timeout: float = 5.0) -> list[dict[str, Any]]:
    """Return page targets from ``/json/list`` (each with ``webSocketDebuggerUrl``)."""
    data: Any = _http_json(base.rstrip("/") + "/json/list", timeout=timeout)
    if isinstance(data, list):
        return [t for t in data if isinstance(t, dict) and t.get("type") == "page"]
    return []


def version(base: str = DEFAULT_BASE, timeout: float = 5.0) -> dict[str, Any]:
    """Return browser version info from ``/json/version``."""
    data: Any = _http_json(base.rstrip("/") + "/json/version", timeout=timeout)
    if not isinstance(data, dict):
        raise ValueError(f"expected JSON object from {base}/json/version")
    return data


def open_page(url: str, base: str = DEFAULT_BASE, timeout: float = 5.0) -> dict[str, Any]:
    """Open a new tab via ``/json/new`` and return its target."""
    data: Any = _http_json(
        base.rstrip("/") + "/json/new?" + urllib.parse.quote(url, safe=""),
        method="PUT",
        timeout=timeout,
    )
    if not isinstance(data, dict):
        raise ValueError(f"expected JSON object from {base}/json/new")
    return data


def pick_page(targets: Iterable[dict[str, Any]], match: str = "") -> dict[str, Any] | None:
    """Pick the first page whose URL contains ``match`` (else the first page)."""
    items = list(targets)
    if match:
        for t in items:
            if match in t.get("url", ""):
                return t
    return items[0] if items else None


# ─── Minimal RFC 6455 WebSocket ───────────────────────────────────────────


def _read_exact(sock: socket.socket, n: int) -> bytes:
    chunks = bytearray()
    while len(chunks) < n:
        part = sock.recv(n - len(chunks))
        if not part:
            raise ConnectionError("websocket closed mid-frame")
        chunks.extend(part)
    return bytes(chunks)


class CDPSession:
    """A WebSocket session to a single CDP page target.

    Supports the small subset of CDP this module needs: ``Runtime.evaluate``,
    ``Page.navigate`` and ``Input.dispatchMouseEvent`` (scrolling).
    """

    def __init__(self, ws_url: str, timeout: float = 15.0) -> None:
        self.ws_url = ws_url
        self.timeout = timeout
        self._sock: socket.socket | None = None
        self._next_id = 1

    # ── connection lifecycle ────────────────────────────────────────────

    def __enter__(self) -> CDPSession:
        self.connect()
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()

    def connect(self) -> None:
        parts = self.ws_url.split("/")
        host_port = parts[2]
        host, _, port_str = host_port.partition(":")
        port = int(port_str or 80)
        sock = socket.create_connection((host, port), timeout=self.timeout)
        sock.settimeout(self.timeout)
        # Sec-WebSocket-Key must be 16 bytes base64-encoded per RFC 6455;
        # generate a 22-char base64-ish value directly to avoid an import.
        _b64 = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/"
        key = "".join(_b64[b % 64] for b in os.urandom(16)) + "=="
        path = "/" + "/".join(parts[3:])
        req = (
            f"GET {path} HTTP/1.1\r\n"
            f"Host: {host_port}\r\n"
            "Upgrade: websocket\r\n"
            "Connection: Upgrade\r\n"
            f"Sec-WebSocket-Key: {key}\r\n"
            "Sec-WebSocket-Version: 13\r\n"
            "\r\n"
        )
        sock.sendall(req.encode("ascii"))
        handshake = self._read_until_headers(sock)
        first = handshake.split(b"\r\n", 1)[0].decode("ascii", "replace")
        if " 101 " not in first:
            raise ConnectionError(f"websocket upgrade failed: {first}")
        self._sock = sock

    @staticmethod
    def _read_until_headers(sock: socket.socket) -> bytes:
        data = bytearray()
        while b"\r\n\r\n" not in data:
            chunk = sock.recv(4096)
            if not chunk:
                raise ConnectionError("websocket closed during handshake")
            data.extend(chunk)
            if len(data) > 16 * 1024:
                raise ConnectionError("handshake headers too large")
        return bytes(data)

    def close(self) -> None:
        if self._sock is not None:
            try:
                self._sock.close()
            finally:
                self._sock = None

    # ── low-level frames ────────────────────────────────────────────────

    def _send_frame(self, opcode: int, payload: bytes) -> None:
        if self._sock is None:
            raise ConnectionError("session not connected")
        header = bytearray([0x80 | opcode])
        length = len(payload)
        if length < 126:
            header.append(0x80 | length)
        elif length < 65536:
            header.append(0x80 | 126)
            header.extend(struct.pack(">H", length))
        else:
            header.append(0x80 | 127)
            header.extend(struct.pack(">Q", length))
        mask = os.urandom(4)
        header.extend(mask)
        masked = bytes(b ^ mask[i % 4] for i, b in enumerate(payload))
        self._sock.sendall(bytes(header) + masked)

    def _recv_frame(self) -> tuple[bool, int, bytes]:
        """Return ``(fin, opcode, payload)`` for one frame."""
        if self._sock is None:
            raise ConnectionError("session not connected")
        b0, b1 = _read_exact(self._sock, 2)
        fin = bool(b0 & 0x80)
        opcode = b0 & 0x0F
        length = b1 & 0x7F
        if length == 126:
            length = struct.unpack(">H", _read_exact(self._sock, 2))[0]
        elif length == 127:
            length = struct.unpack(">Q", _read_exact(self._sock, 8))[0]
        if length > FRAME_MAX:
            raise ConnectionError(f"frame too large: {length}")
        mask_key = _read_exact(self._sock, 4) if b1 & 0x80 else None
        payload = _read_exact(self._sock, length)
        if mask_key:
            payload = bytes(b ^ mask_key[i % 4] for i, b in enumerate(payload))
        return fin, opcode, payload

    def _send_json(self, obj: dict[str, Any]) -> None:
        self._send_frame(0x1, json.dumps(obj).encode("utf-8"))

    def _recv_json(self) -> dict[str, Any]:
        """Read a complete (possibly fragmented) JSON text message."""
        buf = bytearray()
        while True:
            fin, opcode, payload = self._recv_frame()
            if opcode == 0x9:  # ping → pong
                self._send_frame(0xA, payload)
                continue
            if opcode == 0x8:  # close
                raise ConnectionError("websocket closed by peer")
            if opcode in (0x1, 0x2, 0x0):
                buf.extend(payload)
                if fin:
                    try:
                        parsed: Any = json.loads(bytes(buf).decode("utf-8"))
                    except json.JSONDecodeError:
                        if len(buf) > FRAME_MAX:
                            raise
                        continue
                    if not isinstance(parsed, dict):
                        raise RuntimeError("CDP websocket message is not a JSON object")
                    return parsed

    # ── CDP calls ──────────────────────────────────────────────────────

    def send(
        self, method: str, params: dict[str, Any] | None = None, timeout: float | None = None
    ) -> dict[str, Any]:
        """Send a CDP method, wait for the matching response, return its result."""
        if self._sock is None:
            raise ConnectionError("session not connected")
        msg_id = self._next_id
        self._next_id += 1
        self._send_json({"id": msg_id, "method": method, "params": params or {}})
        deadline = timeout or self.timeout
        self._sock.settimeout(deadline)
        while True:
            resp = self._recv_json()
            if resp.get("id") != msg_id:
                continue  # event or stale response; ignore
            if "error" in resp:
                err = resp["error"]
                raise RuntimeError(f"CDP {method} failed: {err}")
            result: Any = resp.get("result", {})
            if not isinstance(result, dict):
                raise RuntimeError(f"CDP {method} returned a non-dict result")
            return result

    def evaluate(self, expression: str, await_promise: bool = True) -> Any:
        """Evaluate JS in the page and return the deserialized value.

        The expression must be a self-contained expression (wrap an IIFE with
        ``(() => {...})()`` when you need statements).
        """
        result = self.send(
            "Runtime.evaluate",
            {"expression": expression, "returnByValue": True, "awaitPromise": await_promise},
        )
        remote = result.get("result", {})
        if remote.get("subtype") == "error":
            raise RuntimeError(f"page JS error: {remote.get('description', 'unknown')}")
        return remote.get("value")

    def navigate(self, url: str) -> None:
        self.send("Page.enable", {})
        self.send("Page.navigate", {"url": url})

    def scroll(self, delta_y: int = 4000, x: int = 0, y: int = 0) -> None:
        """Dispatch a mouse-wheel event to scroll the page (CSS pixels)."""
        self.send(
            "Input.dispatchMouseEvent",
            {
                "type": "mouseWheel",
                "x": x,
                "y": y,
                "deltaX": 0,
                "deltaY": delta_y,
                "modifiers": 0,
            },
        )


# ─── CLI ───────────────────────────────────────────────────────────────────


def _cli() -> int:
    parser = argparse.ArgumentParser(
        prog="x_cdp", description="CDP client for a running Edge/Chrome"
    )
    parser.add_argument(
        "--endpoint", default=os.environ.get("X_BROWSER_CDP_ENDPOINT", DEFAULT_BASE)
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    sub.add_parser("list", help="list open page targets")
    p_eval = sub.add_parser("eval", help="evaluate JS on a page")
    p_eval.add_argument("expression")
    p_nav = sub.add_parser("nav", help="navigate a page")
    p_nav.add_argument("url")
    for p in (p_eval, p_nav):
        p.add_argument("--match", default="", help="URL substring to pick the page")

    args = parser.parse_args()

    try:
        if args.cmd == "list":
            for t in discover(args.endpoint):
                print(f"{t.get('url', '')}\n    {t.get('title', '')}")
            return 0

        target = pick_page(discover(args.endpoint), args.match)
        if target is None:
            print("no page target found", file=sys.stderr)
            return 1
        ws = target["webSocketDebuggerUrl"]
        with CDPSession(ws) as cdp:
            if args.cmd == "eval":
                print(json.dumps(cdp.evaluate(args.expression), ensure_ascii=False))
            elif args.cmd == "nav":
                cdp.navigate(args.url)
                time.sleep(3)
                print(
                    json.dumps(
                        cdp.evaluate("location.href + ' || ' + document.title"),
                        ensure_ascii=False,
                    )
                )
        return 0
    except Exception as e:  # noqa: BLE001
        print(f"error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(_cli())
