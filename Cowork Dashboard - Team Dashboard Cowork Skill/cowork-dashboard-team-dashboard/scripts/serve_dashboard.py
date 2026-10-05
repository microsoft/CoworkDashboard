#!/usr/bin/env python3
"""Serve only the verified public dashboard on loopback; never run jobs or commands."""
import argparse
from functools import partial
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import sys
from urllib.parse import unquote, urlsplit
import webbrowser

import verify_dashboard


FILES = {
    "/": ("index.html", "text/html; charset=utf-8"),
    "/index.html": ("index.html", "text/html; charset=utf-8"),
    "/assets/dashboard.js": ("assets/dashboard.js", "text/javascript; charset=utf-8"),
    "/assets/dashboard.css": ("assets/dashboard.css", "text/css; charset=utf-8"),
    "/dashboard-data.json": ("dashboard-data.json", "application/json; charset=utf-8"),
    "/dashboard-glossary.json": ("dashboard-glossary.json", "application/json; charset=utf-8"),
    "/team-summary.md": ("team-summary.md", "text/markdown; charset=utf-8"),
}


class Handler(BaseHTTPRequestHandler):
    def __init__(self, *args, root, **kwargs):
        self.root = root
        super().__init__(*args, **kwargs)

    def respond(self, status, body, content_type="text/plain; charset=utf-8"):
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("Content-Security-Policy",
                         "default-src 'none'; script-src 'self'; style-src 'self' 'unsafe-inline'; "
                         "connect-src 'self'; img-src 'self'; base-uri 'none'; "
                         "form-action 'none'; frame-ancestors 'none'")
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(body)

    def serve(self):
        port = self.server.server_port
        hosts = {f"127.0.0.1:{port}", f"localhost:{port}"}
        if self.headers.get_all("Host") is None or len(self.headers.get_all("Host")) != 1:
            return self.respond(421, b"One loopback Host header is required.")
        if self.headers["Host"] not in hosts:
            return self.respond(421, b"Invalid Host.")
        origin = self.headers.get("Origin")
        if origin is not None and origin not in {f"http://{host}" for host in hosts}:
            return self.respond(403, b"Cross-origin requests are not allowed.")
        if self.command not in {"GET", "HEAD"}:
            return self.respond(405, b"This server is read-only; no commands or refresh jobs.")
        try:
            target = urlsplit(self.path)
        except ValueError:
            return self.respond(400, b"Malformed request target.")
        decoded = unquote(target.path)
        if (target.scheme or target.netloc or "\\" in decoded or "\x00" in decoded
                or any(part in {".", ".."} for part in decoded.split("/"))):
            return self.respond(400, b"Invalid path.")
        if decoded.startswith("/run/"):
            return self.respond(405, b"Job execution is not supported.")
        if decoded == "/health":
            return self.respond(200, json.dumps({"service": "cowork-team-dashboard",
                                                "readOnly": True}).encode(),
                                "application/json; charset=utf-8")
        resource = FILES.get(decoded)
        if resource is None:
            return self.respond(404, b"Not a public dashboard file.")
        relative, content_type = resource
        path = (self.root / relative).resolve()
        if not path.is_relative_to(self.root):
            return self.respond(400, b"Path escapes the public site.")
        try:
            body = path.read_bytes()
        except FileNotFoundError:
            return self.respond(404, b"Dashboard asset missing; rebuild the site.")
        except OSError as exc:
            print(f"[serve_dashboard] cannot read {relative}: {exc}", file=sys.stderr)
            return self.respond(500, b"Cannot read dashboard asset; see server log.")
        return self.respond(200, body, content_type)

    do_GET = serve
    do_HEAD = serve
    do_POST = serve
    do_PUT = serve
    do_DELETE = serve
    do_OPTIONS = serve
    do_PATCH = serve


def make_server(directory, port=7333):
    root = Path(directory).resolve()
    errors = verify_dashboard.verify(str(root / "index.html"))
    if errors:
        raise ValueError("Dashboard verification failed: " + "; ".join(errors))
    return ThreadingHTTPServer(("127.0.0.1", port), partial(Handler, root=root))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dir", default="output/team-dashboard")
    parser.add_argument("--port", type=int, default=7333)
    parser.add_argument("--no-open", action="store_true")
    args = parser.parse_args()
    if not 1 <= args.port <= 65535:
        parser.error("--port must be between 1 and 65535")
    try:
        server = make_server(args.dir, args.port)
    except (OSError, ValueError) as exc:
        parser.exit(1, f"[serve_dashboard] cannot start: {exc}\n")
    with server:
        url = f"http://127.0.0.1:{server.server_port}/"
        print(f"[serve_dashboard] read-only local site: {url}", flush=True)
        if not args.no_open:
            try:
                opened = webbrowser.open(url)
            except webbrowser.Error as exc:
                print(f"[serve_dashboard] browser could not open: {exc}; open {url} yourself",
                      file=sys.stderr)
            else:
                if not opened:
                    print(f"[serve_dashboard] browser unavailable; open {url} yourself",
                          file=sys.stderr)
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            print("\n[serve_dashboard] stopped")


if __name__ == "__main__":
    main()
