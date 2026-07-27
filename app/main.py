import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

try:
    from app.orchestrator import Orchestrator
except ModuleNotFoundError:
    from orchestrator import Orchestrator


orchestrator = Orchestrator()


class BridgeAIHandler(BaseHTTPRequestHandler):
    def _send_json(self, payload: dict, status: int = 200) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        # Permissive CORS so the browser can call this directly if the Vite dev
        # proxy isn't used. Preflights are answered in do_OPTIONS below.
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self) -> None:
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Content-Length", "0")
        self.end_headers()

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
        try:
            payload = json.loads(body.decode("utf-8")) if body else {}
        except (ValueError, UnicodeDecodeError):
            self._send_json({"error": "Invalid JSON body"}, 400)
            return

        question = payload.get("question", "")
        try:
            result = orchestrator.handle(question)
        except Exception as exc:  # noqa: BLE001 - never leak a stack trace to the client
            self._send_json(
                {"source": "Salesforce", "answer": f"Server error: {exc}",
                 "count": 0, "people": [], "error": str(exc)},
                500,
            )
            return
        self._send_json(result)

    def log_message(self, format: str, *args) -> None:
        return


if __name__ == "__main__":
    server = ThreadingHTTPServer(("127.0.0.1", 8000), BridgeAIHandler)
    print("Bridge AI Interface PoC running on http://127.0.0.1:8000")
    server.serve_forever()
