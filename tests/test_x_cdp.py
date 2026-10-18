"""x_cdp 协议层测试：用手写的最小 WebSocket 服务端验证 RFC 6455 正确性。

覆盖 PR #45 review 中发现并修复的真实缺陷：
  1. Sec-WebSocket-Key 必须是 16 字节 base64（24 字符），旧实现生成 18 字符非法 base64
  2. 必须校验 Sec-WebSocket-Accept，旧实现完全不校验
  3. 握手响应与首个 frame 同包到达时，leftover 字节不能被丢弃
  4. 非 JSON 消息不能导致死循环

这些测试不触网、不依赖浏览器。
"""

import base64
import contextlib
import hashlib
import json
import socket
import struct
import sys
import threading
import time
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from x_cdp import CDPSession  # noqa: E402

GUID = "258EAFA5-E914-47DA-95CA-C5AB0DC85B11"


# ── helpers ────────────────────────────────────────────────────────────────


def make_frame(payload: bytes, opcode: int = 0x1) -> bytes:
    """Server→client frame (unmasked)."""
    header = bytearray([0x80 | opcode])
    n = len(payload)
    if n < 126:
        header.append(n)
    elif n < 65536:
        header.append(126)
        header.extend(struct.pack(">H", n))
    else:
        header.append(127)
        header.extend(struct.pack(">Q", n))
    return bytes(header) + payload


class MiniWSServer:
    """Single-shot WebSocket server used to script exact byte sequences."""

    def __init__(
        self,
        *,
        accept_override=None,
        coalesce=True,
        extra_frames=b"",
        bad_accept=False,
        status="101 Switching Protocols",
    ):
        self.accept_override = accept_override
        self.coalesce = coalesce
        self.extra_frames = extra_frames
        self.bad_accept = bad_accept
        self.status = status
        self.received_key = None
        self.received_frames: list[bytes] = []
        self._srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._srv.bind(("127.0.0.1", 0))
        self._srv.listen(1)
        self.port = self._srv.getsockname()[1]
        self._thread = threading.Thread(target=self._serve, daemon=True)

    def __enter__(self):
        self._thread.start()
        return self

    def __exit__(self, *exc):
        with contextlib.suppress(OSError):
            self._srv.close()

    @property
    def url(self) -> str:
        return f"ws://127.0.0.1:{self.port}/devtools/page/TEST"

    def _read_http_request(self, conn) -> str:
        data = b""
        while b"\r\n\r\n" not in data:
            chunk = conn.recv(4096)
            if not chunk:
                return data.decode("latin-1")
            data += chunk
        return data.decode("latin-1")

    def _read_client_frame(self, conn) -> bytes:
        head = conn.recv(2)
        if len(head) < 2:
            return b""
        length = head[1] & 0x7F
        if length == 126:
            length = struct.unpack(">H", conn.recv(2))[0]
        elif length == 127:
            length = struct.unpack(">Q", conn.recv(8))[0]
        mask = conn.recv(4)
        payload = b""
        while len(payload) < length:
            chunk = conn.recv(length - len(payload))
            if not chunk:
                break
            payload += chunk
        return bytes(b ^ mask[i % 4] for i, b in enumerate(payload))

    def _serve(self):
        try:
            conn, _ = self._srv.accept()
        except OSError:
            return
        try:
            req = self._read_http_request(conn)
            key = ""
            for line in req.split("\r\n"):
                if line.lower().startswith("sec-websocket-key:"):
                    key = line.split(":", 1)[1].strip()
            self.received_key = key

            if self.accept_override is not None:
                accept = self.accept_override
            else:
                accept = base64.b64encode(hashlib.sha1((key + GUID).encode()).digest()).decode()
            if self.bad_accept:
                accept = "wrong-accept-value"

            resp = (
                f"HTTP/1.1 {self.status}\r\n"
                "Upgrade: websocket\r\n"
                "Connection: Upgrade\r\n"
                f"Sec-WebSocket-Accept: {accept}\r\n"
                "\r\n"
            ).encode()

            if self.coalesce:
                # Handshake and the first frame in the SAME write: reproduces
                # the leftover-data race that used to drop frames.
                conn.sendall(resp + self.extra_frames)
            else:
                conn.sendall(resp)
                time.sleep(0.05)
                if self.extra_frames:
                    conn.sendall(self.extra_frames)

            # Echo one client frame so tests can assert client→server works.
            conn.settimeout(1.5)
            with contextlib.suppress(TimeoutError, OSError):
                self.received_frames.append(self._read_client_frame(conn))
        finally:
            conn.close()


def cdp_response(msg_id: int, value: str) -> bytes:
    return make_frame(json.dumps({"id": msg_id, "result": {"result": {"value": value}}}).encode())


# ── 缺陷 1: key 必须是合法 RFC 6455 key ────────────────────────────────────


def test_websocket_key_is_valid_rfc6455():
    """旧实现生成 18 字符非法 base64；RFC 6455 要求 16 字节 base64 → 24 字符。"""
    with MiniWSServer(bad_accept=False, extra_frames=b"") as srv, CDPSession(srv.url, timeout=2.0):
        pass
    key = srv.received_key
    assert key is not None
    assert len(key) == 24, f"key must be 24 chars, got {len(key)}: {key!r}"
    decoded = base64.b64decode(key, validate=True)
    assert len(decoded) == 16


# ── 缺陷 2: 必须校验 Sec-WebSocket-Accept ──────────────────────────────────


def test_rejects_wrong_websocket_accept():
    """错误的 Sec-WebSocket-Accept 必须被拒绝（RFC 6455 §4.1）。"""
    with MiniWSServer(bad_accept=True) as srv, pytest.raises(ConnectionError, match="accept"):
        CDPSession(srv.url, timeout=2.0).connect()


def test_accepts_correct_websocket_accept():
    with MiniWSServer(bad_accept=False) as srv:
        session = CDPSession(srv.url, timeout=2.0)
        session.connect()
        session.close()


# ── 缺陷 3: 握手同包的 frame 不能丢 ────────────────────────────────────────


def test_frame_coalesced_with_handshake_is_not_lost():
    """握手响应与首个 frame 同 TCP 包到达时必须被读到。

    旧实现 recv(4096) 越过 header 边界后把那些字节丢弃，导致客户端永远等不到响应。
    """
    with (
        MiniWSServer(coalesce=True, extra_frames=cdp_response(1, "delivered")) as srv,
        CDPSession(srv.url, timeout=3.0) as cdp,
    ):
        result = cdp.send("Runtime.evaluate", {"expression": "1"})
    assert result["result"]["value"] == "delivered"


def test_frame_arriving_after_handshake_still_works():
    """分离到达的 frame 也要正常工作（确保修复没有引入回归）。"""
    with (
        MiniWSServer(coalesce=False, extra_frames=cdp_response(1, "separate")) as srv,
        CDPSession(srv.url, timeout=3.0) as cdp,
    ):
        result = cdp.send("Runtime.evaluate", {"expression": "1"})
    assert result["result"]["value"] == "separate"


# ── 缺陷 4: 非 JSON 消息不能死循环 ─────────────────────────────────────────


def test_non_json_message_raises_instead_of_hanging():
    """非 JSON 消息应抛错，而不是在同一 buffer 上无限循环。"""
    garbage = make_frame(b"this is not json at all")
    with (
        MiniWSServer(extra_frames=garbage) as srv,
        CDPSession(srv.url, timeout=1.0) as cdp,
        pytest.raises(RuntimeError, match="non-JSON"),
    ):
        cdp.send("Runtime.evaluate", {"expression": "1"})


# ── 握手失败路径 ───────────────────────────────────────────────────────────


def test_non_101_handshake_raises():
    with (
        MiniWSServer(status="403 Forbidden") as srv,
        pytest.raises(ConnectionError, match="upgrade failed"),
    ):
        CDPSession(srv.url, timeout=2.0).connect()


# ── 客户端 mask 与 ping/pong ──────────────────────────────────────────────


def test_client_frames_are_masked():
    """RFC 6455 §5.3: 客户端发出的 frame 必须带 mask。"""
    with (
        MiniWSServer(coalesce=True, extra_frames=cdp_response(1, "ok")) as srv,
        CDPSession(srv.url, timeout=3.0) as cdp,
    ):
        cdp.send("Runtime.evaluate", {"expression": "1"})
        time.sleep(0.2)
    assert srv.received_frames, "server did not receive a client frame"
    sent = srv.received_frames[0].decode("utf-8", "replace")
    assert "Runtime.evaluate" in sent
