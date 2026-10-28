"""Read-only browser page for the ERC-20 PFT token's state on Base.

Run from the repository root::

    PYTHONPATH=python python3 -m postfiat_rpc.pft_token_ui \\
      --record crates/pft-token-contracts/deployments/pft-token-base-84532/deployment.json

``/api/state`` runs the ``pft_token`` reader with the server's configured RPC
URL and record or token, and returns its JSON plus ``fetched_at``. Besides the
page and its two assets there is no other route, and every method but GET is
refused: the service never signs or sends a transaction.
"""

from __future__ import annotations

import argparse
import json
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Callable, Sequence
from urllib.parse import urlsplit

from postfiat_rpc import pft_token

ASSET_DIR = Path(__file__).with_name("pft_token_ui_assets")
STATIC_ROUTES = {
    "/": ("index.html", "text/html"),
    "/app.js": ("app.js", "text/javascript"),
    "/styles.css": ("styles.css", "text/css"),
}
SECURITY_HEADERS = {
    "x-content-type-options": "nosniff",
    "x-frame-options": "DENY",
    "referrer-policy": "no-referrer",
    "content-security-policy": "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self'; "
    "connect-src 'self'; object-src 'none'; base-uri 'none'; form-action 'none'; frame-ancestors 'none'",
}


class PftTokenUiServer(ThreadingHTTPServer):
    reader: Callable[[], dict[str, Any]]


class PftTokenUiHandler(BaseHTTPRequestHandler):
    server: PftTokenUiServer

    def log_message(self, format_string: str, *args: object) -> None:
        print(f"pft-token-ui: {format_string % args}")

    def __getattr__(self, name: str) -> Any:
        # Every request method other than GET, including unknown ones, is 405.
        if name.startswith("do_"):
            return self._method_not_allowed
        raise AttributeError(name)

    def _send(self, status: HTTPStatus, payload: bytes, content_type: str, **extra: str) -> None:
        self.send_response(status)
        self.send_header("content-type", f"{content_type}; charset=utf-8")
        self.send_header("content-length", str(len(payload)))
        self.send_header("cache-control", "no-store")
        for name, value in {**SECURITY_HEADERS, **extra}.items():
            self.send_header(name, value)
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(payload)

    def _json(self, status: HTTPStatus, value: dict[str, Any], **extra: str) -> None:
        self._send(status, json.dumps(value, sort_keys=True).encode(), "application/json", **extra)

    def _method_not_allowed(self) -> None:
        self._json(HTTPStatus.METHOD_NOT_ALLOWED, {"error": "read-only interface: GET only"}, allow="GET")

    def do_GET(self) -> None:  # noqa: N802
        path = urlsplit(self.path).path
        if path == "/api/state":
            fetched_at = pft_token.utc_iso()
            try:
                state = self.server.reader()
            except pft_token.PftTokenError as error:
                refused = isinstance(error, pft_token.PftTokenRefused)
                body = {"error": str(error), "refused": refused, "fetched_at": fetched_at}
                self._json(HTTPStatus.BAD_GATEWAY, body)
                return
            self._json(HTTPStatus.OK, {**state, "fetched_at": fetched_at})
            return
        route = STATIC_ROUTES.get(path)
        if route is None:
            self._json(HTTPStatus.NOT_FOUND, {"error": "not found"})
            return
        asset, content_type = route
        self._send(HTTPStatus.OK, (ASSET_DIR / asset).read_bytes(), content_type)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m postfiat_rpc.pft_token_ui",
        description="Serve a read-only page with the ERC-20 PFT token's state on Base.",
    )
    parser.add_argument("--rpc-url", default=pft_token.DEFAULT_RPC_URL)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--record", metavar="PATH", help="a deployment.json record: token, treasury and chain id")
    source.add_argument("--token", metavar="ADDRESS", help="the token address on Base or Base Sepolia")
    parser.add_argument("--treasury", metavar="ADDRESS", help="the treasury address (default from the record)")
    parser.add_argument("--timeout", type=float, default=pft_token.TIMEOUT_SECONDS)
    parser.add_argument("--port", type=int, default=8766, help="port on 127.0.0.1 (0 picks a free one)")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if not 0 <= args.port <= 65535:
        raise SystemExit("--port must be between 0 and 65535")
    if args.token and not args.treasury:
        raise SystemExit("--treasury is required with --token")

    def reader() -> dict[str, Any]:
        return pft_token.read_token_state(
            args.rpc_url, record=args.record, token=args.token, treasury=args.treasury, timeout=args.timeout
        )

    server = PftTokenUiServer(("127.0.0.1", args.port), PftTokenUiHandler)
    server.reader = reader
    host, port = server.server_address[:2]
    print(f"PFT token state: http://{host}:{port}")
    print(f"Read-only: GET only, RPC {pft_token.redact_rpc_url(args.rpc_url)}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
