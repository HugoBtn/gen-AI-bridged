import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

try:
    from app.orchestrator import Orchestrator
except ModuleNotFoundError:
    from orchestrator import Orchestrator


orchestrator = Orchestrator()


class BridgeAIHandler(BaseHTTPRequestHandler):
    def _send_json(self, payload: dict, status: int = 200) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:
        if self.path == "/health":
            self._send_json({"status": "ok", "service": "bridge-ai-interface-poc"})
            return
        self._send_json({"error": "Not found"}, 404)

    def do_POST(self) -> None:
        if self.path != "/chat":
            self._send_json({"error": "Not found"}, 404)
            return

        content_length = int(self.headers.get("Content-Length", "0"))
        body = self.rfile.read(content_length)
        payload = json.loads(body.decode("utf-8"))
        question = payload.get("question", "")
        result = orchestrator.handle(question)
        self._send_json(result)

    def log_message(self, format: str, *args) -> None:
        return


if __name__ == "__main__":
    server = ThreadingHTTPServer(("127.0.0.1", 8000), BridgeAIHandler)
    print("Bridge AI Interface PoC running on http://127.0.0.1:8000")
    server.serve_forever()
