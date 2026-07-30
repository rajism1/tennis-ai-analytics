"""
Tennis AI Video Event Labeling & Accuracy Verification Backend Server
Serves the web dashboard, streams match.mp4 video with HTTP Byte-Range seeking support,
and manages REST API for verifying/correcting event telemetry.
"""

import http.server
import socketserver
import json
import os
import sys
import re
import argparse
import pandas as pd
from analytics_engine import AnalyticsEngine

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
WEB_DIR = os.path.join(BASE_DIR, "web_annotator")
OUTPUT_DIR = os.path.join(BASE_DIR, "output")

JSON_PATH = os.path.join(OUTPUT_DIR, "tennis_match_analytics.json")
CSV_PATH = os.path.join(OUTPUT_DIR, "tennis_match_analytics.csv")
VERIFIED_CSV_PATH = os.path.join(OUTPUT_DIR, "tennis_match_analytics_verified.csv")

# Auto-detect match2.mp4 if present so video stream matches snapshot gallery
if os.path.exists(os.path.join(BASE_DIR, "match2.mp4")):
    VIDEO_PATH = os.path.join(BASE_DIR, "match2.mp4")
else:
    VIDEO_PATH = os.path.join(BASE_DIR, "match.mp4")

class LabelingHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
    def translate_path(self, path):
        # Serve static web dashboard files
        if path.startswith("/api/"):
            return path
            
        req_path = path.split('?', 1)[0].split('#', 1)[0]
        if req_path == "/" or req_path == "/index.html":
            return os.path.join(WEB_DIR, "index.html")
        elif os.path.exists(os.path.join(WEB_DIR, req_path.lstrip("/"))):
            return os.path.join(WEB_DIR, req_path.lstrip("/"))
            
        return super().translate_path(path)

    def do_GET(self):
        if self.path.startswith("/api/events"):
            self.send_json_events()
        elif self.path.startswith("/api/player_analytics"):
            self.send_player_analytics()
        elif self.path.startswith("/api/export_csv"):
            self.export_verified_csv()
        elif self.path.startswith("/api/video"):
            self.stream_video()
        elif self.path.startswith("/api/snapshot/"):
            self.serve_snapshot()
        else:
            # Send cache control headers to prevent stale browser JS/CSS caching
            self.send_response(200) if self.path != "/" else None
            super().do_GET()

    def end_headers(self):
        self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
        self.send_header("Pragma", "no-cache")
        self.send_header("Expires", "0")
        super().end_headers()

    def send_player_analytics(self):
        # Extract player parameter if provided: /api/player_analytics?player=Player%201
        player_id = "Player 1"
        if "player=" in self.path:
            player_id = re.search(r'player=([^&]+)', self.path).group(1).replace("%20", " ")

        engine = AnalyticsEngine()
        if os.path.exists(JSON_PATH):
            with open(JSON_PATH, "r") as f:
                try:
                    engine.records = json.load(f)
                except Exception:
                    engine.records = []

        res_data = engine.compute_player_analytics(target_player=player_id)
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps(res_data).encode('utf-8'))

    def serve_snapshot(self):
        filename = os.path.basename(self.path)
        snapshot_path = os.path.join(OUTPUT_DIR, "snapshots", filename)
        if os.path.exists(snapshot_path):
            with open(snapshot_path, "rb") as f:
                data = f.read()
            self.send_response(200)
            self.send_header('Content-Type', 'image/jpeg')
            self.send_header('Content-Length', str(len(data)))
            self.end_headers()
            self.wfile.write(data)
        else:
            self.send_error(404, "Snapshot not found")

    def do_POST(self):
        if self.path.startswith("/api/events"):
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            events = json.loads(post_data.decode('utf-8'))
            
            # Save updated JSON
            with open(JSON_PATH, "w") as f:
                json.dump(events, f, indent=2)
                
            # Export updated verified CSV
            df = pd.DataFrame(events)
            df.to_csv(VERIFIED_CSV_PATH, index=False)
            df.to_csv(CSV_PATH, index=False)
            
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({"status": "success", "count": len(events)}).encode('utf-8'))

    def send_json_events(self):
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        
        events = []
        if os.path.exists(JSON_PATH):
            with open(JSON_PATH, "r") as f:
                try:
                    events = json.load(f)
                except Exception:
                    events = []
        
        self.wfile.write(json.dumps(events).encode('utf-8'))

    def export_verified_csv(self):
        if os.path.exists(VERIFIED_CSV_PATH):
            with open(VERIFIED_CSV_PATH, "rb") as f:
                data = f.read()
            self.send_response(200)
            self.send_header('Content-type', 'text/csv')
            self.send_header('Content-Disposition', 'attachment; filename="tennis_match_analytics_verified.csv"')
            self.end_headers()
            self.wfile.write(data)
        else:
            self.send_error(404, "Verified CSV not found")

    def stream_video(self):
        """Streams video with HTTP Range header support for seeking in HTML5 Video."""
        target_video = VIDEO_PATH
        if not os.path.exists(target_video):
            target_video = os.path.join(OUTPUT_DIR, "my_match_analyzed.mp4")
            
        if not os.path.exists(target_video):
            self.send_error(404, "Match video file not found.")
            return

        file_size = os.path.getsize(target_video)
        range_header = self.headers.get('Range')

        if range_header:
            byte_match = re.search(r'bytes=(\d+)-(\d*)', range_header)
            start_byte = int(byte_match.group(1))
            end_byte = int(byte_match.group(2)) if byte_match.group(2) else file_size - 1
            length = end_byte - start_byte + 1

            self.send_response(206)
            self.send_header('Content-Type', 'video/mp4')
            self.send_header('Content-Range', f'bytes {start_byte}-{end_byte}/{file_size}')
            self.send_header('Content-Length', str(length))
            self.send_header('Accept-Ranges', 'bytes')
            self.end_headers()

            with open(target_video, 'rb') as f:
                f.seek(start_byte)
                self.wfile.write(f.read(length))
        else:
            self.send_response(200)
            self.send_header('Content-Type', 'video/mp4')
            self.send_header('Content-Length', str(file_size))
            self.send_header('Accept-Ranges', 'bytes')
            self.end_headers()
            with open(target_video, 'rb') as f:
                self.wfile.write(f.read())

def run_server(port=8080):
    print(f"\n=======================================================")
    print(f"🎾 Tennis AI Event Labeling & Accuracy Verification Server")
    print(f"=======================================================")
    print(f"Server URL: http://localhost:{port}")
    print(f"Reading events from: {JSON_PATH}")
    print(f"Streaming video from: {VIDEO_PATH}")
    print(f"Press Ctrl+C to stop the server.\n")

    Handler = LabelingHTTPRequestHandler
    socketserver.TCPServer.allow_reuse_address = True
    with socketserver.TCPServer(("", port), Handler) as httpd:
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nShutting down server.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Tennis AI Event Labeling Server")
    parser.add_argument("--port", type=int, default=8080, help="Port to run web server on")
    args = parser.parse_args()

    run_server(args.port)
