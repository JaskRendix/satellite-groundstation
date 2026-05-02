import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

from .metrics import metrics


class _PrometheusHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path != "/metrics":
            self.send_response(404)
            self.end_headers()
            return

        snapshot = metrics.snapshot()
        output = []

        for key, value in snapshot.items():
            safe_key = key.replace(".", "_")
            output.append(f"{safe_key} {value}")

        data = "\n".join(output).encode()

        self.send_response(200)
        self.send_header("Content-Type", "text/plain")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)


def start_prometheus_exporter(port: int = 9100) -> None:
    """
    Start a simple Prometheus exporter in a background thread.
    """
    server = HTTPServer(("0.0.0.0", port), _PrometheusHandler)

    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()


def export_metrics_json(path: str) -> None:
    """
    Write metrics snapshot to a JSON file.
    """
    snapshot = metrics.snapshot()
    with open(path, "w") as f:
        json.dump(snapshot, f, indent=2)
