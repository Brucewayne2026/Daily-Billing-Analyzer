"""
MedBill Dashboard - Local Server
=================================
Saves dashboard data to: dashboard_data.json  (same folder as this script)
Usage:  python server.py
Then open your browser to:  http://localhost:8765
"""

import json
import os
import sys
import re
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse
import webbrowser
import threading

# ── Config ──────────────────────────────────────────────────────────────
PORT         = 8765
BASE_DIR     = os.path.dirname(os.path.abspath(__file__))
DATA_FILE    = os.path.join(BASE_DIR, "dashboard_data.json")
REASONS_FILE = os.path.join(BASE_DIR, "pending_reasons.json")
DASHBOARD    = os.path.join(BASE_DIR, "Billing dashboard.html")
CHARTJS      = os.path.join(BASE_DIR, "chart.min.js")
CHARTJS_URL  = "https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.1/chart.umd.min.js"

# ── Paste PIN (never exposed to browser) ────────────────────────────────
PASTE_PIN = "123456"
# ────────────────────────────────────────────────────────────────────────


def update_paste_pin_in_server(new_pin):
    """Rewrite the PASTE_PIN value directly inside this server.py file."""
    global PASTE_PIN
    server_file = os.path.abspath(__file__)
    try:
        with open(server_file, "r", encoding="utf-8") as f:
            src = f.read()
        new_src = re.sub(
            r'(PASTE_PIN\s*=\s*")[^"]*(")',
            lambda m: m.group(1) + new_pin + m.group(2),
            src
        )
        with open(server_file, "w", encoding="utf-8") as f:
            f.write(new_src)
        PASTE_PIN = new_pin
        print(f"  ✔  PASTE_PIN updated in server.py")
        return True
    except Exception as e:
        print(f"  ⚠  Could not update PASTE_PIN: {e}")
        return False


def ensure_chartjs():
    if os.path.exists(CHARTJS):
        return
    print("  Downloading Chart.js for local serving (one-time)...")
    try:
        import urllib.request
        urllib.request.urlretrieve(CHARTJS_URL, CHARTJS)
        print(f"  ✔  Chart.js saved → {CHARTJS}")
    except Exception as e:
        print(f"  ⚠  Could not download Chart.js: {e}")
        print(   "     Make sure you have internet on first run, then it works offline forever.")


def load_reasons():
    if os.path.exists(REASONS_FILE):
        try:
            with open(REASONS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            return {}
    return {}


def save_reasons(data):
    try:
        with open(REASONS_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        print(f"  ✔  Pending reasons saved → {REASONS_FILE}")
    except Exception as e:
        print(f"  ⚠  Failed to save reasons: {e}")


class Handler(BaseHTTPRequestHandler):

    def log_message(self, fmt, *args):
        if args and len(args) > 1:
            code = str(args[1])
            if code in ('200', '304', '404', '10053', '10054'):
                return
        super().log_message(fmt, *args)

    def _headers(self, content_type="application/json", status=200):
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Access-Control-Allow-Origin",  "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Cache-Control", "no-store")
        self.end_headers()

    def do_OPTIONS(self):
        self._headers()

    def do_GET(self):
        path = urlparse(self.path).path

        if path in ("/", "/index.html", "/billing_dashboard.html"):
            if not os.path.exists(DASHBOARD):
                self._headers("text/plain", 404)
                self.wfile.write(f"'{os.path.basename(DASHBOARD)}' not found next to server.py".encode())
                return
            with open(DASHBOARD, "rb") as f:
                data = f.read()
            self._headers("text/html; charset=utf-8")
            self.wfile.write(data)

        elif path == "/chart.min.js":
            if not os.path.exists(CHARTJS):
                self._headers("text/plain", 404)
                self.wfile.write(b"chart.min.js not found")
                return
            with open(CHARTJS, "rb") as f:
                data = f.read()
            self.send_response(200)
            self.send_header("Content-Type", "application/javascript")
            self.send_header("Cache-Control", "max-age=86400")
            self.end_headers()
            self.wfile.write(data)

        elif path == "/style.css":
            css_file = os.path.join(BASE_DIR, "style.css")
            if not os.path.exists(css_file):
                self._headers("text/plain", 404)
                self.wfile.write(b"style.css not found")
                return
            with open(css_file, "rb") as f:
                data = f.read()
            self.send_response(200)
            self.send_header("Content-Type", "text/css")
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(data)

        elif path.startswith("/img/"):
            img_file = os.path.join(BASE_DIR, path.lstrip("/"))
            if not os.path.exists(img_file):
                self._headers("text/plain", 404)
                self.wfile.write(f"Image not found: {path}".encode())
                return
            ext  = os.path.splitext(img_file)[1].lower()
            mime = {".png": "image/png", ".jpg": "image/jpeg",
                    ".jpeg": "image/jpeg", ".gif": "image/gif",
                    ".svg": "image/svg+xml", ".ico": "image/x-icon"
                    }.get(ext, "application/octet-stream")
            with open(img_file, "rb") as f:
                data = f.read()
            self.send_response(200)
            self.send_header("Content-Type", mime)
            self.send_header("Cache-Control", "max-age=86400")
            self.end_headers()
            self.wfile.write(data)

        elif path == "/api/load":
            if os.path.exists(DATA_FILE):
                with open(DATA_FILE, "rb") as f:
                    payload = f.read()
                self._headers("application/json")
                self.wfile.write(payload)
            else:
                self._headers("application/json")
                self.wfile.write(b"null")

        elif path == "/api/pending-reasons":
            reasons = load_reasons()
            self._headers("application/json")
            self.wfile.write(json.dumps(reasons).encode())

        else:
            self._headers("text/plain", 404)
            self.wfile.write(b"Not found")

    def do_POST(self):
        path   = urlparse(self.path).path
        length = int(self.headers.get("Content-Length", 0))
        body   = self.rfile.read(length)

        # ── Verify paste PIN ─────────────────────────────────────────
        if path == "/api/verify-pin":
            try:
                data = json.loads(body)
                if data.get("pin") == PASTE_PIN:
                    self._headers()
                    self.wfile.write(json.dumps({"ok": True}).encode())
                else:
                    self._headers("application/json", 401)
                    self.wfile.write(json.dumps({"ok": False}).encode())
            except Exception as e:
                self._headers("application/json", 500)
                self.wfile.write(json.dumps({"ok": False, "error": str(e)}).encode())

        # ── Change paste PIN (requires current PIN to authorize) ──────
        elif path == "/api/change-pin":
            try:
                data        = json.loads(body)
                current_pin = data.get("current_pin", "")
                new_pin     = data.get("new_pin", "").strip()

                if current_pin != PASTE_PIN:
                    self._headers("application/json", 401)
                    self.wfile.write(json.dumps({"ok": False, "error": "Current password is incorrect."}).encode())
                    return

                if len(new_pin) < 6:
                    self._headers("application/json", 400)
                    self.wfile.write(json.dumps({"ok": False, "error": "New password must be at least 6 characters."}).encode())
                    return

                success = update_paste_pin_in_server(new_pin)
                if success:
                    self._headers()
                    self.wfile.write(json.dumps({"ok": True}).encode())
                else:
                    self._headers("application/json", 500)
                    self.wfile.write(json.dumps({"ok": False, "error": "Could not write new password to server.py"}).encode())

            except Exception as e:
                self._headers("application/json", 500)
                self.wfile.write(json.dumps({"ok": False, "error": str(e)}).encode())

        # ── Save dashboard data ──────────────────────────────────────
        elif path == "/api/save":
            try:
                json.loads(body)
                with open(DATA_FILE, "wb") as f:
                    f.write(body)
                self._headers()
                self.wfile.write(json.dumps({"ok": True, "file": DATA_FILE}).encode())
                print(f"  ✔  Data saved → {DATA_FILE}")
            except Exception as e:
                self._headers("application/json", 500)
                self.wfile.write(json.dumps({"ok": False, "error": str(e)}).encode())

        # ── Save pending reasons ─────────────────────────────────────
        elif path == "/api/pending-reasons":
            try:
                data = json.loads(body)
                save_reasons(data)
                self._headers()
                self.wfile.write(json.dumps({"ok": True}).encode())
            except Exception as e:
                print(f"  ⚠  Error saving reasons: {e}")
                self._headers("application/json", 500)
                self.wfile.write(json.dumps({"ok": False, "error": str(e)}).encode())

        else:
            self._headers("text/plain", 404)
            self.wfile.write(b"Not found")


def open_browser():
    import time
    time.sleep(0.8)
    webbrowser.open(f"http://localhost:{PORT}")


if __name__ == "__main__":
    if not os.path.exists(DASHBOARD):
        print(f"\n⚠  Could not find:  {DASHBOARD}")
        print(   "   Make sure 'Billing dashboard.html' is in the SAME folder as server.py\n")
        sys.exit(1)

    ensure_chartjs()

    print(f"\n{'='*54}")
    print(f"  Intellircm Dashboard Server")
    print(f"{'='*54}")
    print(f"  Folder       : {BASE_DIR}")
    print(f"  Data file    : {DATA_FILE}")
    print(f"  Your URL     : http://localhost:{PORT}")
    print(f"  Friend's URL : http://10.6.0.12:{PORT}")
    print(f"{'='*54}")
    print(f"  Press Ctrl+C to stop the server.\n")

    threading.Thread(target=open_browser, daemon=True).start()

    server = HTTPServer(("0.0.0.0", PORT), Handler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n  Server stopped.")