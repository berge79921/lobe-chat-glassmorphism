#!/usr/bin/env python3
"""
Internal MCP bridge: stdio MCP server -> private HTTP API.

This bridge is intended for private in-cluster usage only.
It wraps a stdio-based MCP server process and exposes:
- GET  /health
- GET  /tools
- POST /tools/call  { "name": "...", "arguments": { ... } }
- POST /tool/<name> { ...arguments... }
- POST /rpc         { "method": "...", "params": { ... } }
"""

from __future__ import annotations

import json
import os
import shlex
import signal
import subprocess
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlparse


BRIDGE_NAME = os.getenv("MCP_BRIDGE_NAME", "mcp-bridge").strip() or "mcp-bridge"
BRIDGE_PORT = int(os.getenv("MCP_BRIDGE_PORT", "8070"))
BRIDGE_HOST = os.getenv("MCP_BRIDGE_HOST", "0.0.0.0")
MCP_COMMAND = os.getenv("MCP_BRIDGE_COMMAND", "").strip()
MCP_CWD = os.getenv("MCP_BRIDGE_CWD", "/srv/mcp").strip() or "/srv/mcp"
REQUEST_TIMEOUT_SEC = int(os.getenv("MCP_BRIDGE_REQUEST_TIMEOUT_SEC", "1200"))
INIT_TIMEOUT_SEC = int(os.getenv("MCP_BRIDGE_INIT_TIMEOUT_SEC", "45"))
MCP_PROTOCOL_VERSION = os.getenv("MCP_PROTOCOL_VERSION", "2024-11-05")
MCP_BRIDGE_STDIO_PROTOCOL = (
    os.getenv("MCP_BRIDGE_STDIO_PROTOCOL", "jsonl").strip().lower() or "jsonl"
)


def _log(msg: str) -> None:
    print(f"[{BRIDGE_NAME}] {msg}", file=sys.stderr, flush=True)


class StdioMcpClient:
    def __init__(self, command: str, cwd: str):
        if not command:
            raise RuntimeError("MCP_BRIDGE_COMMAND is required")

        argv = shlex.split(command)
        if not argv:
            raise RuntimeError("MCP_BRIDGE_COMMAND could not be parsed")

        if not Path(cwd).exists():
            raise RuntimeError(f"MCP_BRIDGE_CWD does not exist: {cwd}")

        child_env = os.environ.copy()
        self._proc = subprocess.Popen(
            argv,
            cwd=cwd,
            env=child_env,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            bufsize=0,
        )
        if not self._proc.stdin or not self._proc.stdout or not self._proc.stderr:
            raise RuntimeError("Failed to open MCP process stdio pipes")

        self._lock = threading.Lock()
        self._next_id = 1
        self._initialized = False
        self._responses: dict[object, dict] = {}
        self._response_cv = threading.Condition()
        self._reader_error: Exception | None = None
        self._stdio_protocol = (
            "content-length"
            if MCP_BRIDGE_STDIO_PROTOCOL in {"content-length", "lsp"}
            else "jsonl"
        )

        self._stderr_thread = threading.Thread(
            target=self._forward_stderr, name=f"{BRIDGE_NAME}-stderr", daemon=True
        )
        self._stderr_thread.start()
        self._stdout_thread = threading.Thread(
            target=self._forward_stdout, name=f"{BRIDGE_NAME}-stdout", daemon=True
        )
        self._stdout_thread.start()

    def _forward_stderr(self) -> None:
        assert self._proc.stderr is not None
        while True:
            line = self._proc.stderr.readline()
            if not line:
                return
            try:
                text = line.decode("utf-8", errors="replace").rstrip()
            except Exception:
                text = repr(line)
            _log(f"mcp: {text}")

    def _forward_stdout(self) -> None:
        while True:
            try:
                message = self._read_message()
            except EOFError:
                with self._response_cv:
                    self._reader_error = EOFError("MCP process stdout closed")
                    self._response_cv.notify_all()
                return
            except Exception as exc:
                _log(f"mcp stdout reader failed: {exc}")
                with self._response_cv:
                    self._reader_error = exc
                    self._response_cv.notify_all()
                return

            message_id = None
            if isinstance(message, dict):
                message_id = message.get("id")
            if message_id is None:
                continue
            with self._response_cv:
                # Prevent response cache leak from timed out requests (max 1000 entries)
                if len(self._responses) > 1000:
                    keys_to_remove = list(self._responses.keys())[:200]
                    for k in keys_to_remove:
                        self._responses.pop(k, None)

                self._responses[message_id] = message
                self._responses[str(message_id)] = message
                self._response_cv.notify_all()

    def is_alive(self) -> bool:
        return self._proc.poll() is None

    def _write_message(self, message: dict) -> None:
        assert self._proc.stdin is not None
        body_text = json.dumps(message, separators=(",", ":"), ensure_ascii=False)
        if self._stdio_protocol == "content-length":
            body = body_text.encode("utf-8")
            header = f"Content-Length: {len(body)}\r\n\r\n".encode("ascii")
            self._proc.stdin.write(header)
            self._proc.stdin.write(body)
        else:
            # MCP SDK >= 1.0 uses line-delimited JSON over stdio.
            self._proc.stdin.write((body_text + "\n").encode("utf-8"))
        self._proc.stdin.flush()

    def _read_message_content_length(self) -> dict:
        assert self._proc.stdout is not None

        headers: dict[str, str] = {}
        while True:
            line = self._proc.stdout.readline()
            if not line:
                raise EOFError("MCP process stdout closed")
            if line in (b"\n", b"\r\n"):
                break
            decoded = line.decode("ascii", errors="ignore").strip()
            if not decoded or ":" not in decoded:
                continue
            key, value = decoded.split(":", 1)
            headers[key.strip().lower()] = value.strip()

        content_length = int(headers.get("content-length", "0"))
        if content_length <= 0:
            raise RuntimeError("Missing or invalid Content-Length in MCP response")

        payload = self._proc.stdout.read(content_length)
        if len(payload) != content_length:
            raise RuntimeError("Unexpected EOF while reading MCP response body")
        return json.loads(payload.decode("utf-8"))

    def _read_message_jsonl(self) -> dict:
        assert self._proc.stdout is not None

        while True:
            line = self._proc.stdout.readline()
            if not line:
                raise EOFError("MCP process stdout closed")

            text = line.decode("utf-8", errors="replace").strip()
            if not text:
                continue

            # Compatibility fallback if a server still emits LSP framing.
            if text.lower().startswith("content-length:"):
                headers = {"content-length": text.split(":", 1)[1].strip()}
                while True:
                    header_line = self._proc.stdout.readline()
                    if not header_line:
                        raise EOFError("MCP process stdout closed while reading headers")
                    if header_line in (b"\n", b"\r\n"):
                        break
                    decoded = header_line.decode("ascii", errors="ignore").strip()
                    if not decoded or ":" not in decoded:
                        continue
                    key, value = decoded.split(":", 1)
                    headers[key.strip().lower()] = value.strip()

                content_length = int(headers.get("content-length", "0"))
                if content_length <= 0:
                    raise RuntimeError("Missing or invalid Content-Length in MCP response")
                payload = self._proc.stdout.read(content_length)
                if len(payload) != content_length:
                    raise RuntimeError("Unexpected EOF while reading MCP response body")
                return json.loads(payload.decode("utf-8"))

            return json.loads(text)

    def _read_message(self) -> dict:
        if self._stdio_protocol == "content-length":
            return self._read_message_content_length()
        return self._read_message_jsonl()

    def request(self, method: str, params: dict | None = None, timeout_sec: int | None = None):
        if not self.is_alive():
            raise RuntimeError("MCP process is not running")

        timeout = timeout_sec or REQUEST_TIMEOUT_SEC
        deadline = time.monotonic() + timeout

        with self._lock:
            req_id = self._next_id
            self._next_id += 1

            request: dict[str, object] = {"jsonrpc": "2.0", "id": req_id, "method": method}
            if params is not None:
                request["params"] = params
            self._write_message(request)

        while True:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise TimeoutError(f"MCP request timed out: {method}")
            with self._response_cv:
                message = self._responses.pop(req_id, None)
                if message is None:
                    message = self._responses.pop(str(req_id), None)
                    if message is not None:
                        self._responses.pop(req_id, None)
                else:
                    self._responses.pop(str(req_id), None)
                if message is not None:
                    if "error" in message:
                        raise RuntimeError(f"MCP error for {method}: {message['error']}")
                    return message.get("result")
                if self._reader_error is not None:
                    raise RuntimeError(f"MCP stdout reader error: {self._reader_error}")
                self._response_cv.wait(timeout=remaining)

    def notify(self, method: str, params: dict | None = None) -> None:
        if not self.is_alive():
            return
        with self._lock:
            msg: dict[str, object] = {"jsonrpc": "2.0", "method": method}
            if params is not None:
                msg["params"] = params
            self._write_message(msg)

    def initialize(self):
        result = self.request(
            "initialize",
            {
                "protocolVersion": MCP_PROTOCOL_VERSION,
                "capabilities": {},
                "clientInfo": {"name": BRIDGE_NAME, "version": "1.0.0"},
            },
            timeout_sec=INIT_TIMEOUT_SEC,
        )
        self.notify("notifications/initialized", {})
        self._initialized = True
        return result

    def close(self) -> None:
        if self._proc.poll() is not None:
            return
        try:
            self._proc.terminate()
            self._proc.wait(timeout=5)
        except Exception:
            try:
                self._proc.kill()
            except Exception:
                pass


def _json_response(handler: BaseHTTPRequestHandler, status: int, payload: dict):
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.send_header("Cache-Control", "no-store")
    handler.send_header("Content-Length", str(len(body)))
    handler.end_headers()
    handler.wfile.write(body)


def make_handler(client: StdioMcpClient):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, format: str, *args):
            _log(f"http: {self.address_string()} {format % args}")

        def _read_json(self) -> dict:
            content_length = int(self.headers.get("Content-Length", "0"))
            if content_length <= 0:
                return {}
            raw = self.rfile.read(content_length)
            if not raw:
                return {}
            return json.loads(raw.decode("utf-8"))

        def do_GET(self):  # noqa: N802
            parsed = urlparse(self.path)
            if parsed.path == "/health":
                return _json_response(
                    self,
                    200 if client.is_alive() else 503,
                    {
                        "ok": client.is_alive(),
                        "bridge": BRIDGE_NAME,
                        "initialized": True,
                    },
                )

            if parsed.path == "/tools":
                try:
                    tools = client.request("tools/list", {})
                    return _json_response(self, 200, {"ok": True, "result": tools})
                except Exception as exc:
                    return _json_response(self, 502, {"ok": False, "error": str(exc)})

            if parsed.path == "/":
                return _json_response(
                    self,
                    200,
                    {
                        "ok": True,
                        "bridge": BRIDGE_NAME,
                        "endpoints": ["/health", "/tools", "/tools/call", "/tool/<name>", "/rpc"],
                    },
                )

            return _json_response(self, 404, {"ok": False, "error": "not_found"})

        def do_POST(self):  # noqa: N802
            parsed = urlparse(self.path)
            try:
                payload = self._read_json()
            except Exception:
                return _json_response(self, 400, {"ok": False, "error": "invalid_json"})

            try:
                if parsed.path == "/tools/call":
                    tool_name = str(payload.get("name", "")).strip()
                    arguments = payload.get("arguments") or {}
                    if not tool_name:
                        return _json_response(self, 400, {"ok": False, "error": "missing_tool_name"})
                    result = client.request("tools/call", {"name": tool_name, "arguments": arguments})
                    return _json_response(self, 200, {"ok": True, "result": result})

                if parsed.path.startswith("/tool/"):
                    tool_name = unquote(parsed.path[len("/tool/") :]).strip()
                    arguments = payload if isinstance(payload, dict) else {}
                    if not tool_name:
                        return _json_response(self, 400, {"ok": False, "error": "missing_tool_name"})
                    result = client.request("tools/call", {"name": tool_name, "arguments": arguments})
                    return _json_response(self, 200, {"ok": True, "result": result})

                if parsed.path == "/rpc":
                    method = str(payload.get("method", "")).strip()
                    params = payload.get("params") if isinstance(payload.get("params"), dict) else {}
                    if not method:
                        return _json_response(self, 400, {"ok": False, "error": "missing_method"})
                    result = client.request(method, params)
                    return _json_response(self, 200, {"ok": True, "result": result})

                return _json_response(self, 404, {"ok": False, "error": "not_found"})
            except TimeoutError as exc:
                return _json_response(self, 504, {"ok": False, "error": str(exc)})
            except Exception as exc:  # Keep bridge failure explicit for operator visibility.
                return _json_response(self, 502, {"ok": False, "error": str(exc)})

    return Handler


def main() -> int:
    _log(f"starting bridge on {BRIDGE_HOST}:{BRIDGE_PORT}")
    _log(f"mcp command: {MCP_COMMAND}")
    _log(f"mcp cwd: {MCP_CWD}")
    _log(f"stdio protocol: {MCP_BRIDGE_STDIO_PROTOCOL}")

    client = StdioMcpClient(command=MCP_COMMAND, cwd=MCP_CWD)
    try:
        init_result = client.initialize()
        _log(f"mcp initialized: {json.dumps(init_result, ensure_ascii=False)}")
    except Exception:
        client.close()
        raise

    server = ThreadingHTTPServer((BRIDGE_HOST, BRIDGE_PORT), make_handler(client))

    stop_event = threading.Event()

    def _shutdown(*_args):
        if stop_event.is_set():
            return
        stop_event.set()
        _log("shutdown requested")
        server.shutdown()

    signal.signal(signal.SIGINT, _shutdown)
    signal.signal(signal.SIGTERM, _shutdown)

    try:
        server.serve_forever(poll_interval=0.5)
    finally:
        _log("stopping bridge")
        server.server_close()
        client.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
