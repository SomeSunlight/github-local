#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import ssl
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path


def operation_name(query: str) -> str:
    match = re.search(r"\b(?:query|mutation)\s+([A-Za-z_][A-Za-z0-9_]*)", query)
    if match:
        return match.group(1)
    if "__type" in query and "Issue" in query:
        return "Issue_fields"
    return "unknown"


def response_for(op: str, variables: dict, host: str) -> tuple[int, dict]:
    repo = {
        "id": "R_gl_probe", "databaseId": 1, "name": variables.get("name") or variables.get("repo") or "demo",
        "owner": {"login": variables.get("owner", "local")}, "hasIssuesEnabled": True, "viewerPermission": "ADMIN",
    }
    if op == "Issue_fields":
        return 200, {"data": {"Issue": {"fields": []}}}
    if op == "IssueRepositoryInfo":
        return 200, {"data": {"repository": repo}}
    if op == "IssueCreate":
        return 200, {"data": {"createIssue": {"issue": {"id": "I_gl_probe_1", "url": f"https://{host}/local/demo/issues/1"}}}}
    if op == "IssueList":
        issue = {"id":"I_gl_probe_1","number":1,"title":"Trace me","state":"OPEN","body":"Protocol probe","url":f"https://{host}/local/demo/issues/1","createdAt":"2026-09-28T18:00:00Z"}
        return 200, {"data": {"repository": {"hasIssuesEnabled": True, "issues": {"totalCount": 1, "nodes": [issue], "pageInfo": {"hasNextPage": False, "endCursor": None}}}}}
    if op == "IssueByNumber":
        issue = {"__typename":"Issue","id":"I_gl_probe_1","number":1,"title":"Trace me","state":"OPEN","body":"Protocol probe","url":f"https://{host}/local/demo/issues/1","createdAt":"2026-09-28T18:00:00Z"}
        return 200, {"data": {"repository": {"hasIssuesEnabled": True, "issue": issue}}}
    if op == "CommentCreate":
        return 200, {"data":{"addComment":{"commentEdge":{"node":{"url":f"https://{host}/local/demo/issues/1#issuecomment-probe"}}}}}
    if op == "IssueClose":
        return 200, {"data":{"closeIssue":{"issue":{"id":"I_gl_probe_1"}}}}
    return 200, {"errors": [{"type":"NOT_IMPLEMENTED","message": f"trace server does not implement GraphQL operation {op}"}]}


class Handler(BaseHTTPRequestHandler):
    server_version = "github-local-trace/0.1"

    def log_message(self, fmt, *args):
        return

    def _record(self, body: bytes, op: str | None, variables: dict | None) -> None:
        selected = {}
        for key in ("Host", "Authorization", "Content-Type", "User-Agent", "X-Github-Api-Version"):
            value = self.headers.get(key)
            if value is not None:
                selected[key.lower()] = "<redacted>" if key == "Authorization" else value
        record = {
            "time": datetime.now(timezone.utc).isoformat(),
            "method": self.command,
            "path": self.path,
            "headers": selected,
            "graphql_operation": op,
            "variables": variables,
            "body": body.decode("utf-8", errors="replace"),
        }
        with self.server.log_path.open("a", encoding="utf-8", newline="\n") as handle:
            handle.write(json.dumps(record, ensure_ascii=False, separators=(",", ":")) + "\n")

    def _json(self, status: int, payload: dict) -> None:
        data = json.dumps(payload, separators=(",", ":")).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        self._record(b"", None, None)
        if self.path.rstrip("/").endswith("/api/v3/meta") or self.path.rstrip("/").endswith("/meta"):
            self._json(200, {"installed_version":"3.20.0"})
            return
        self._json(404, {"message":"trace server: unhandled GET"})

    def do_POST(self):
        length = int(self.headers.get("Content-Length", "0"))
        body = self.rfile.read(length)
        try:
            payload = json.loads(body or b"{}")
        except json.JSONDecodeError:
            self._record(body, None, None)
            self._json(400, {"message":"invalid JSON"})
            return
        query = str(payload.get("query", ""))
        variables = payload.get("variables") or {}
        op = operation_name(query)
        self._record(body, op, variables)
        if self.path not in ("/api/graphql", "/graphql"):
            self._json(404, {"message":"trace server: expected GraphQL endpoint"})
            return
        status, response = response_for(op, variables, self.headers.get("Host", "github.localhost"))
        self._json(status, response)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--listen", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8443)
    parser.add_argument("--cert")
    parser.add_argument("--key")
    parser.add_argument("--log", type=Path, default=Path("gh-trace.jsonl"))
    args = parser.parse_args()
    args.log.parent.mkdir(parents=True, exist_ok=True)
    server = ThreadingHTTPServer((args.listen, args.port), Handler)
    server.log_path = args.log
    if bool(args.cert) != bool(args.key):
        parser.error("--cert and --key must be supplied together")
    if args.cert:
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        context.load_cert_chain(args.cert, args.key)
        server.socket = context.wrap_socket(server.socket, server_side=True)
    scheme = "https" if args.cert else "http"
    print(f"trace server: {scheme}://{args.listen}:{args.port} -> {args.log}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
