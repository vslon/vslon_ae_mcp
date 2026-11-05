"""Protocol tests for ae_mcp_server.py against a fake CEP bridge (no After Effects needed).

Run:  python -m unittest discover -s tests -v
"""
import json
import os
import socket
import subprocess
import sys
import threading
import unittest
from http.server import BaseHTTPRequestHandler, HTTPServer

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SERVER = os.path.join(ROOT, "server", "ae_mcp_server.py")


class FakeBridge(BaseHTTPRequestHandler):
    """Mimics extension/js/bridge.js. The reply to /eval is chosen by markers in the code."""

    last_code = None

    def log_message(self, *a):
        pass

    def _send(self, obj, status=200):
        body = json.dumps(obj).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path == "/ping":
            self._send({"ok": True, "app": "After Effects", "port": self.server.server_port})
        else:
            self._send({"ok": False, "error": "not found"}, 404)

    def do_POST(self):
        code = json.loads(self.rfile.read(int(self.headers["Content-Length"])))["code"]
        FakeBridge.last_code = code
        if "__FAIL__" in code:
            result = json.dumps({"ok": False, "error": "Error: boom", "line": 3})
        elif "__EMPTY__" in code:
            result = ""
        elif "app.version" in code:
            result = json.dumps({"ok": True, "value": {"version": "26.0x1", "project": None, "items": 0}})
        else:
            result = json.dumps({"ok": True, "value": 42})
        self._send({"ok": True, "result": result})


def free_port():
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port


class ServerTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.port = free_port()
        cls.httpd = HTTPServer(("127.0.0.1", cls.port), FakeBridge)
        threading.Thread(target=cls.httpd.serve_forever, daemon=True).start()
        env = dict(os.environ, AE_MCP_PORT=str(cls.port))
        cls.proc = subprocess.Popen([sys.executable, SERVER], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                    env=env, text=True, bufsize=1)
        cls.next_id = 0

    @classmethod
    def tearDownClass(cls):
        cls.proc.stdin.close()
        cls.proc.wait(5)
        cls.proc.stdout.close()
        cls.httpd.shutdown()
        cls.httpd.server_close()

    def rpc(self, method, params=None):
        ServerTest.next_id += 1
        msg = {"jsonrpc": "2.0", "id": self.next_id, "method": method, "params": params or {}}
        self.proc.stdin.write(json.dumps(msg) + "\n")
        self.proc.stdin.flush()
        resp = json.loads(self.proc.stdout.readline())
        self.assertEqual(resp["id"], self.next_id)
        return resp

    def call(self, name, args=None):
        return self.rpc("tools/call", {"name": name, "arguments": args or {}})["result"]

    def test_initialize(self):
        r = self.rpc("initialize", {"protocolVersion": "2024-11-05"})["result"]
        self.assertEqual(r["serverInfo"]["name"], "after-effects")
        self.assertIn("tools", r["capabilities"])

    def test_tools_list(self):
        tools = {t["name"]: t for t in self.rpc("tools/list")["result"]["tools"]}
        for name in ("ae_ping", "ae_run_jsx", "ae_run_jsx_file", "ae_project_info", "ae_comp_layers",
                     "ae_save_frame_png", "ae_render_queue_add", "ae_render", "ae_save_project", "ae_open_project"):
            self.assertIn(name, tools)
            self.assertEqual(tools[name]["inputSchema"]["type"], "object")
        self.assertEqual(tools["ae_run_jsx"]["inputSchema"]["required"], ["code"])

    def test_ping(self):
        r = self.call("ae_ping")
        self.assertFalse(r.get("isError", False))
        data = json.loads(r["content"][0]["text"])
        self.assertTrue(data["bridge"]["ok"])
        self.assertEqual(data["ae"]["version"], "26.0x1")

    def test_run_jsx_wraps_code(self):
        r = self.call("ae_run_jsx", {"code": "return 6*7;"})
        self.assertEqual(r["content"][0]["text"], "42")
        code = FakeBridge.last_code
        self.assertIn("app.beginSuppressDialogs()", code)
        self.assertIn("return 6*7;", code)

    def test_extendscript_error(self):
        r = self.call("ae_run_jsx", {"code": "__FAIL__"})
        self.assertTrue(r["isError"])
        self.assertIn("line 3", r["content"][0]["text"])

    def test_empty_result(self):
        r = self.call("ae_run_jsx", {"code": "__EMPTY__"})
        self.assertTrue(r["isError"])
        self.assertIn("syntax error", r["content"][0]["text"])

    def test_string_escaping(self):
        self.call("ae_comp_layers", {"comp": 'My "comp" \\ 01'})
        self.assertIn(json.dumps('My "comp" \\ 01'), FakeBridge.last_code)

    def test_unknown_tool(self):
        r = self.call("ae_nope")
        self.assertTrue(r["isError"])

    def test_unknown_method(self):
        self.assertEqual(self.rpc("foo/bar")["error"]["code"], -32601)


if __name__ == "__main__":
    unittest.main()
