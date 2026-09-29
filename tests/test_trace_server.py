from __future__ import annotations

import json
import tempfile
import threading
import unittest
import urllib.request
from http.server import ThreadingHTTPServer
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "spike"))
import gh_trace_server


class TraceServerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.log = Path(self.temp.name) / "trace.jsonl"
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), gh_trace_server.Handler)
        self.server.log_path = self.log
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.base = f"http://127.0.0.1:{self.server.server_address[1]}"

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join()
        self.temp.cleanup()

    def post(self, operation, query, variables):
        data = json.dumps({"query":query,"variables":variables,"operationName":operation}).encode()
        req = urllib.request.Request(self.base + "/api/graphql", data=data, headers={"Content-Type":"application/json","Authorization":"token secret"})
        with urllib.request.urlopen(req) as response:
            return json.load(response)

    def test_issue_repository_and_create_are_canned_and_logged(self):
        repo = self.post("IssueRepositoryInfo", "query IssueRepositoryInfo($owner:String!,$name:String!){repository(owner:$owner,name:$name){id}}", {"owner":"local","name":"demo"})
        self.assertEqual("R_gl_probe", repo["data"]["repository"]["id"])
        created = self.post("IssueCreate", "mutation IssueCreate($input:CreateIssueInput!){createIssue(input:$input){issue{id url}}}", {"input":{"repositoryId":"R_gl_probe","title":"x"}})
        self.assertEqual("I_gl_probe_1", created["data"]["createIssue"]["issue"]["id"])
        rows = [json.loads(line) for line in self.log.read_text(encoding="utf-8").splitlines()]
        self.assertEqual(["IssueRepositoryInfo","IssueCreate"], [row["graphql_operation"] for row in rows])
        self.assertEqual("<redacted>", rows[0]["headers"]["authorization"])

    def test_unknown_graphql_operation_fails_loudly(self):
        payload = self.post("Mystery", "query Mystery{viewer{login}}", {})
        self.assertEqual("NOT_IMPLEMENTED", payload["errors"][0]["type"])


if __name__ == "__main__":
    unittest.main()
