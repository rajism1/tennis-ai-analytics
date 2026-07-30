"""
Multi-Threaded HTTP Web Server for Tennis AI Analytics Dashboard (Module 2)
"""

import http.server
import socketserver
import os
import json
import re
import urllib.parse
from .engine import AnalyticsEngine

MODULE_DIR = os.path.dirname(os.path.abspath(__file__))
WEB_DIR = os.path.join(MODULE_DIR, "web")
BASE_DIR = os.path.dirname(MODULE_DIR)
OUTPUT_DIR = os.path.join(BASE_DIR, "output")
JSON_PATH = os.path.join(OUTPUT_DIR, "tennis_match_analytics.json")

class AnalyticsHTTPRequestHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        clean_path = self.path.split('?', 1)[0].split('#', 1)[0]

        if clean_path in ("/", "/index.html"):
            self.serve_index_html()
        elif self.path.startswith("/api/events"):
            self.send_json_events()
        elif self.path.startswith("/api/player_analytics"):
            self.send_player_analytics()
        elif self.path.startswith("/api/export_csv"):
            self.export_verified_csv()
        elif self.path.startswith("/api/snapshot/"):
            self.serve_snapshot()
        else:
            self.serve_static_file(clean_path)

    def serve_static_file(self, req_path):
        relative_path = req_path.lstrip("/")
        full_path = os.path.join(WEB_DIR, relative_path)

        if os.path.exists(full_path) and os.path.isfile(full_path):
            content_type = "text/plain"
            if full_path.endswith(".html"): content_type = "text/html; charset=utf-8"
            elif full_path.endswith(".css"): content_type = "text/css"
            elif full_path.endswith(".js"): content_type = "application/javascript"
            elif full_path.endswith(".png"): content_type = "image/png"
            elif full_path.endswith(".jpg") or full_path.endswith(".jpeg"): content_type = "image/jpeg"
            elif full_path.endswith(".svg"): content_type = "image/svg+xml"

            with open(full_path, "rb") as f:
                data = f.read()

            self.send_response(200)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
            self.send_header("Pragma", "no-cache")
            self.send_header("Expires", "0")
            self.end_headers()
            self.wfile.write(data)
        else:
            self.send_error(404, f"File not found: {req_path}")

    def serve_index_html(self):
        index_path = os.path.join(WEB_DIR, "index.html")
        if not os.path.exists(index_path):
            self.send_error(404, "index.html not found")
            return

        with open(index_path, "r", encoding="utf-8") as f:
            html_content = f.read()

        engine = AnalyticsEngine(output_dir=OUTPUT_DIR)
        if os.path.exists(JSON_PATH):
            with open(JSON_PATH, "r", encoding="utf-8") as f:
                try:
                    engine.records = json.load(f)
                except Exception:
                    engine.records = []

        data_p1 = engine.compute_player_analytics("Player 1")
        data_p2 = engine.compute_player_analytics("Player 2")

        injected_script = f"""
<script>
  window.INITIAL_ANALYTICS_P1 = {json.dumps(data_p1)};
  window.INITIAL_ANALYTICS_P2 = {json.dumps(data_p2)};
  document.addEventListener('DOMContentLoaded', () => {{
    if (typeof renderPlayerAnalyticsUI === 'function') {{
      renderPlayerAnalyticsUI(window.INITIAL_ANALYTICS_P1);
    }}
  }});
</script>
</body>"""

        html_content = html_content.replace("</body>", injected_script)

        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(html_content.encode("utf-8"))))
        self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
        self.send_header("Pragma", "no-cache")
        self.send_header("Expires", "0")
        self.end_headers()
        self.wfile.write(html_content.encode("utf-8"))

    def send_json_events(self):
        if os.path.exists(JSON_PATH):
            with open(JSON_PATH, "rb") as f:
                data = f.read()
        else:
            data = json.dumps([]).encode('utf-8')

        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(data)))
        self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
        self.end_headers()
        self.wfile.write(data)

    def send_player_analytics(self):
        player_id = "Player 1"
        if "player=" in self.path:
            match = re.search(r'player=([^&]+)', self.path)
            if match:
                player_id = urllib.parse.unquote(match.group(1))

        engine = AnalyticsEngine(output_dir=OUTPUT_DIR)
        if os.path.exists(JSON_PATH):
            with open(JSON_PATH, "r", encoding="utf-8") as f:
                try:
                    engine.records = json.load(f)
                except Exception:
                    engine.records = []

        res_data = engine.compute_player_analytics(target_player=player_id)
        data = json.dumps(res_data).encode('utf-8')

        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(data)))
        self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
        self.end_headers()
        self.wfile.write(data)

    def serve_snapshot(self):
        filename = os.path.basename(self.path)
        filepath = os.path.join(OUTPUT_DIR, "snapshots", filename)
        if os.path.exists(filepath) and os.path.isfile(filepath):
            with open(filepath, "rb") as f:
                data = f.read()
            self.send_response(200)
            self.send_header("Content-Type", "image/jpeg")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)
        else:
            self.send_error(404, "Snapshot image not found")

    def export_verified_csv(self):
        engine = AnalyticsEngine(output_dir=OUTPUT_DIR)
        if os.path.exists(JSON_PATH):
            with open(JSON_PATH, "r", encoding="utf-8") as f:
                try:
                    engine.records = json.load(f)
                except Exception:
                    engine.records = []

        csv_path = os.path.join(OUTPUT_DIR, "tennis_match_analytics.csv")
        engine.export_csv(filename="tennis_match_analytics.csv")

        if os.path.exists(csv_path):
            with open(csv_path, "rb") as f:
                data = f.read()
            self.send_response(200)
            self.send_header('Content-Type', 'text/csv')
            self.send_header('Content-Disposition', 'attachment; filename="tennis_match_analytics.csv"')
            self.send_header('Content-Length', str(len(data)))
            self.end_headers()
            self.wfile.write(data)
        else:
            self.send_error(500, "Could not generate CSV file")

def run_server(port=8080):
    print("=" * 55)
    print("🎾 Tennis AI Analytics Dashboard Server (Module 2)")
    print("=" * 55)
    print(f"Dashboard URL: http://localhost:{port}")
    print(f"Telemetry Source: {JSON_PATH}")
    print("Press Ctrl+C to stop the server.\n")

    with http.server.ThreadingHTTPServer(("", port), AnalyticsHTTPRequestHandler) as httpd:
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\n[Server Stopped]")

if __name__ == "__main__":
    run_server()
