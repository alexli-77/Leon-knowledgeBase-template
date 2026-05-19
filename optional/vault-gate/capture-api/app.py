#!/usr/bin/env python3
"""Small standard-library HTTP API for Vault Gate."""

from __future__ import annotations

import argparse
import json
import os
import socketserver
import sys
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

CURATOR_DIR = Path(__file__).resolve().parents[1] / "curator"
sys.path.insert(0, str(CURATOR_DIR))

from vault_gate import GateError, capture, edit_request, load_config  # noqa: E402


class VaultGateServer(ThreadingHTTPServer):
    def server_bind(self) -> None:
        socketserver.TCPServer.server_bind(self)
        host, port = self.server_address[:2]
        self.server_name = str(host)
        self.server_port = int(port)


def token() -> str:
    value = os.environ.get("VAULT_GATE_TOKEN", "").strip()
    if not value:
        raise GateError("VAULT_GATE_TOKEN is required")
    return value


class Handler(BaseHTTPRequestHandler):
    server_version = "VaultGate/0.1"

    def log_message(self, fmt: str, *args: object) -> None:
        return

    def send_json(self, status: int, payload: dict) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def authorized(self) -> bool:
        expected = f"Bearer {token()}"
        return self.headers.get("Authorization", "") == expected

    def do_GET(self) -> None:
        if self.path == "/health":
            self.send_json(HTTPStatus.OK, {"status": "ok"})
            return
        self.send_json(HTTPStatus.NOT_FOUND, {"status": "error", "error": "not found"})

    def do_POST(self) -> None:
        try:
            if not self.authorized():
                self.send_json(HTTPStatus.UNAUTHORIZED, {"status": "error", "error": "unauthorized"})
                return
            length = int(self.headers.get("Content-Length", "0"))
            data = json.loads(self.rfile.read(length).decode("utf-8"))
            source = str(data.get("source", "api"))
            title = str(data.get("title", ""))
            body = str(data.get("body", ""))
            config = load_config()
            if self.path == "/capture":
                result = capture(config, source, title, body)
            elif self.path == "/edit-request":
                result = edit_request(config, source, title, body)
            else:
                self.send_json(HTTPStatus.NOT_FOUND, {"status": "error", "error": "not found"})
                return
            self.send_json(HTTPStatus.OK, result.to_dict())
        except (GateError, ValueError, json.JSONDecodeError) as exc:
            self.send_json(HTTPStatus.BAD_REQUEST, {"status": "error", "error": str(exc)})


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8787)
    args = parser.parse_args()
    token()
    server = VaultGateServer((args.host, args.port), Handler)
    print(f"Vault Gate API listening on http://{args.host}:{args.port}", flush=True)
    server.serve_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
