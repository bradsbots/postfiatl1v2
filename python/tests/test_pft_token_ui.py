"""The read-only PFT token page serves its state and nothing else."""

from __future__ import annotations

import http.client
import json
import re
import threading
import unittest

from postfiat_rpc import pft_token, pft_token_ui

STATE = {
    "schema": pft_token.STATE_SCHEMA,
    "chain_id": 84532,
    "rpc_url": "https://base.example/…",
    "record": "crates/pft-token-contracts/deployments/pft-token-base-84532/deployment.json",
    "token": "0x18fE4ca51A0cE042688D5A54917319d03B527D92",
    "treasury": "0x7424F4F4A620d37CFB54A4558a1Ec7f60b71A0CB",
    "name": "Post Fiat Token",
    "symbol": "PFT",
    "decimals": 6,
    "total_supply_units": "100000000000000000",
    "total_supply_pft": "100000000000",
    "treasury_balance_units": "100000000000000000",
    "treasury_balance_pft": "100000000000",
    "treasury_holds_whole_supply": True,
    "code_size_bytes": 3587,
    "block_number": 51328006,
    "read_at": "2026-10-28T11:37:50Z",
}
EXPLORER_URLS = ("https://base-sepolia.blockscout.com/address/", "https://base.blockscout.com/address/")


class PftTokenUiTests(unittest.TestCase):
    def setUp(self) -> None:
        self.server = pft_token_ui.PftTokenUiServer(("127.0.0.1", 0), pft_token_ui.PftTokenUiHandler)
        self.reader_result: object = STATE
        self.server.reader = self.read
        thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        thread.start()

        def stop() -> None:
            self.server.shutdown()
            self.server.server_close()
            thread.join(timeout=2)

        self.addCleanup(stop)

    def read(self) -> dict:
        if isinstance(self.reader_result, Exception):
            raise self.reader_result
        return dict(self.reader_result)  # type: ignore[arg-type]

    def request(self, method: str, path: str) -> tuple[int, dict[str, str], bytes]:
        connection = http.client.HTTPConnection(*self.server.server_address, timeout=2)
        try:
            connection.request(method, path, body=b"{}" if method in ("POST", "PUT") else None)
            response = connection.getresponse()
            return response.status, {k.lower(): v for k, v in response.getheaders()}, response.read()
        finally:
            connection.close()

    def test_page_and_assets(self) -> None:
        status, headers, body = self.request("GET", "/")
        self.assertEqual(status, 200)
        self.assertTrue(headers["content-type"].startswith("text/html"))
        self.assertIn("default-src 'self'", headers["content-security-policy"])
        html = body.decode()
        for element in ('id="token"', 'id="treasury"', 'id="whole-supply"', 'id="refresh"', 'src="/app.js"'):
            self.assertIn(element, html)
        for path, kind in (("/app.js", "text/javascript"), ("/styles.css", "text/css")):
            status, headers, _ = self.request("GET", path)
            self.assertEqual((status, headers["content-type"].split(";")[0]), (200, kind))

    def test_api_state_returns_the_reader_json_and_fetched_at(self) -> None:
        status, headers, body = self.request("GET", "/api/state")
        self.assertEqual(status, 200)
        self.assertEqual(headers["cache-control"], "no-store")
        payload = json.loads(body)
        fetched_at = payload.pop("fetched_at")
        self.assertRegex(fetched_at, r"^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ$")
        self.assertEqual(payload, STATE)

    def test_api_state_reports_a_refusal_as_502(self) -> None:
        self.reader_result = pft_token.PftTokenRefused("the RPC endpoint is on chain 8453, expected 84532")
        status, _, body = self.request("GET", "/api/state")
        payload = json.loads(body)
        self.assertEqual((status, payload["refused"]), (502, True))
        self.assertIn("expected 84532", payload["error"])

    def test_unknown_path_is_404(self) -> None:
        for path in ("/api/send", "/index.html/../pft_token_ui.py", "/deployment.json"):
            with self.subTest(path=path):
                self.assertEqual(self.request("GET", path)[0], 404)

    def test_every_non_get_method_is_405(self) -> None:
        for method in ("POST", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS", "TRANSFER"):
            with self.subTest(method=method):
                status, headers, _ = self.request(method, "/api/state")
                self.assertEqual((status, headers.get("allow")), (405, "GET"))

    def test_assets_hold_no_secrets_or_external_urls_but_the_explorer(self) -> None:
        for name in ("index.html", "app.js", "styles.css"):
            with self.subTest(asset=name):
                text = (pft_token_ui.ASSET_DIR / name).read_text(encoding="utf-8")
                for url in re.findall(r"(?:https?:)?//[^\s\"'`<>)]+", text):
                    self.assertTrue(url.startswith(EXPLORER_URLS), url)
                self.assertIsNone(re.search(r"api[-_]?key|secret|token=|bearer|password", text, re.IGNORECASE))
                self.assertNotIn("@import", text)
                self.assertNotIn("<script>", text)

    def test_rpc_url_is_shown_redacted(self) -> None:
        self.assertEqual(pft_token.redact_rpc_url("https://base.example/v2/KEY"), STATE["rpc_url"])
        self.assertIn('$("rpc").textContent = state.rpc_url', (pft_token_ui.ASSET_DIR / "app.js").read_text())


if __name__ == "__main__":
    unittest.main()
