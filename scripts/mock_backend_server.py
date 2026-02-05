#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qs, urlparse


def json_bytes(payload: object) -> bytes:
    return json.dumps(payload, ensure_ascii=False).encode("utf-8")


class Handler(BaseHTTPRequestHandler):
    server_version = "ScholarFlowMockBackend/1.0"

    def _send_json(self, status: int, payload: object) -> None:
        body = json_bytes(payload)
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "*")
        self.send_header("Access-Control-Allow-Methods", "GET,POST,PUT,PATCH,DELETE,OPTIONS")
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self) -> None:  # noqa: N802
        self._send_json(204, {})

    def do_GET(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        path = parsed.path
        qs = parse_qs(parsed.query or "")

        if path == "/api/v1/stats/system":
            return self._send_json(200, {"success": True, "data": {"ok": True}})

        if path == "/api/v1/cms/menu":
            # expected shape: {success:true,data:[...]}
            location = (qs.get("location") or [""])[0]
            return self._send_json(200, {"success": True, "data": [], "meta": {"location": location}})

        if path == "/api/v1/manuscripts/published/latest":
            limit = int((qs.get("limit") or ["6"])[0])
            return self._send_json(200, {"success": True, "data": [], "meta": {"limit": limit}})

        if path.startswith("/api/v1/cms/pages/"):
            slug = path.split("/api/v1/cms/pages/", 1)[1]
            return self._send_json(
                200,
                {
                    "success": True,
                    "data": {
                        "slug": slug,
                        "title": slug.replace("-", " ").title(),
                        "content_html": f"<h1>{slug}</h1><p>Mocked CMS page for E2E.</p>",
                        "is_published": True,
                    },
                },
            )

        # Default: return a benign JSON payload
        return self._send_json(200, {"success": True, "data": {}})

    def do_POST(self) -> None:  # noqa: N802
        # Default: accept writes as no-op
        return self._send_json(200, {"success": True, "data": {}})

    def log_message(self, fmt: str, *args) -> None:  # noqa: D401
        # keep logs quiet in CI-like runs
        return


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()

    httpd = HTTPServer((args.host, args.port), Handler)
    print(f"[mock-backend] listening on http://{args.host}:{args.port}", flush=True)
    httpd.serve_forever()


if __name__ == "__main__":
    main()

