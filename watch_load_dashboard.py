#!/usr/bin/env python3
"""Watch load_to_db progress — terminal dashboard or local web UI."""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

from load_progress import STATUS_PATH, get_progress

DASHBOARD_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <title>Municipal AI — Vector DB Load</title>
  <meta http-equiv="refresh" content="2" />
  <style>
    body { font-family: system-ui, sans-serif; max-width: 720px; margin: 2rem auto; padding: 0 1rem; background: #0f172a; color: #e2e8f0; }
    h1 { font-size: 1.25rem; margin-bottom: 0.25rem; }
    .muted { color: #94a3b8; font-size: 0.9rem; }
    .bar { background: #1e293b; border-radius: 999px; height: 28px; overflow: hidden; margin: 1rem 0; border: 1px solid #334155; }
    .fill { background: linear-gradient(90deg, #2563eb, #38bdf8); height: 100%; transition: width 0.4s ease; display: flex; align-items: center; justify-content: center; font-weight: 600; font-size: 0.85rem; min-width: 3rem; }
    .grid { display: grid; grid-template-columns: 1fr 1fr; gap: 0.75rem; }
    .card { background: #1e293b; border: 1px solid #334155; border-radius: 12px; padding: 0.75rem 1rem; }
    .card label { display: block; color: #94a3b8; font-size: 0.75rem; text-transform: uppercase; letter-spacing: 0.04em; }
    .card span { font-size: 1.1rem; font-weight: 600; }
    .done { color: #4ade80; }
    .error { color: #f87171; }
    .running { color: #38bdf8; }
  </style>
</head>
<body>
  <h1>Vector DB load progress</h1>
  <p class="muted">Auto-refreshes every 2s · <code>python3 watch_load_dashboard.py --web</code></p>
  <div class="bar"><div class="fill" id="bar" style="width:0%">0%</div></div>
  <div class="grid" id="stats"></div>
  <p class="muted" id="footer"></p>
  <script>
    fetch('/api/status').then(r => r.json()).then(d => {
      if (!d || d.error) {
        document.getElementById('footer').textContent = d?.error || 'No progress data yet';
        return;
      }
      const pct = d.percent ?? 0;
      document.getElementById('bar').style.width = Math.max(pct, 3) + '%';
      document.getElementById('bar').textContent = pct.toFixed(1) + '%';
      const statusClass = d.status === 'complete' ? 'done' : d.status === 'failed' ? 'error' : 'running';
      const eta = d.eta_seconds != null ? Math.round(d.eta_seconds/60) + ' min' : '—';
      const elapsed = d.seconds_elapsed != null ? Math.round(d.seconds_elapsed/60) + ' min' : '—';
      document.getElementById('stats').innerHTML = [
        ['Status', d.status, statusClass],
        ['Provider', d.provider || '—', ''],
        ['Phase', d.phase || '—', ''],
        ['Documents', (d.documents_embedded||0).toLocaleString() + ' / ' + (d.total_documents||0).toLocaleString(), ''],
        ['Batches', (d.completed_batches||0) + ' / ' + (d.total_batches||0), ''],
        ['Elapsed', elapsed, ''],
        ['ETA', eta, ''],
      ].map(([label, val, cls]) =>
        `<div class="card"><label>${label}</label><span class="${cls}">${val}</span></div>`
      ).join('');
      document.getElementById('footer').textContent =
        'Updated ' + (d.updated_at || '') + (d.source === 'log' ? ' · parsed from log (restart load for live JSON status)' : '');
    }).catch(e => { document.getElementById('footer').textContent = e.message; });
  </script>
</body>
</html>
"""


def _bar(pct: float, width: int = 40) -> str:
    filled = int(width * pct / 100)
    return "█" * filled + "░" * (width - filled)


def terminal_dashboard(refresh: float) -> None:
    while True:
        os.system("clear" if os.name != "nt" else "cls")
        progress = get_progress()
        print("Municipal AI — Vector DB load dashboard")
        print("=" * 50)
        if not progress:
            print("\nNo progress yet. Start: python3 load_to_db.py")
            print(f"Watching: {STATUS_PATH} and load_to_db_ollama.log")
        else:
            pct = progress.get("percent", 0)
            status = progress.get("status", "unknown")
            print(f"\nStatus: {status.upper()}  |  Phase: {progress.get('phase', '?')}")
            print(f"Provider: {progress.get('provider', '?')}")
            print(f"\n[{_bar(pct)}] {pct:.1f}%")
            print(
                f"Documents: {progress.get('documents_embedded', 0):,} / "
                f"{progress.get('total_documents', 0):,}"
            )
            print(
                f"Batches:   {progress.get('completed_batches', 0)} / "
                f"{progress.get('total_batches', 0)}"
            )
            if progress.get("seconds_elapsed") is not None:
                print(
                    f"Elapsed:   {progress['seconds_elapsed'] // 60}m {progress['seconds_elapsed'] % 60}s"
                )
            if progress.get("eta_seconds") is not None:
                eta = progress["eta_seconds"]
                print(f"ETA:       {eta // 60}m {eta % 60}s")
            if progress.get("last_error"):
                print(f"\n❌ {progress['last_error']}")
            if progress.get("source") == "log":
                print(
                    "\n(note: reading tqdm log — next run will write load_status.json)"
                )
            if status == "complete":
                print("\n🎉 Load complete. Run: python3 check_db.py")
                break
            if status == "failed":
                break
        print(f"\nRefreshing every {refresh}s · Ctrl+C to exit")
        time.sleep(refresh)


def run_web_server(host: str, port: int, open_browser: bool) -> None:
    root = Path.cwd()

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *_args) -> None:
            return

        def do_GET(self) -> None:
            if self.path in {"/", "/index.html"}:
                body = DASHBOARD_HTML.encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
                return
            if self.path == "/api/status":
                progress = get_progress()
                body = json.dumps(progress or {"error": "No progress data yet"}).encode(
                    "utf-8"
                )
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                self.wfile.write(body)
                return
            self.send_error(404)

    os.chdir(root)
    url = f"http://{host}:{port}/"
    print(f"Dashboard: {url}")
    print("API:       {url}api/status")
    if open_browser:
        webbrowser.open(url)
    HTTPServer((host, port), Handler).serve_forever()


def main() -> None:
    parser = argparse.ArgumentParser(description="Watch vector DB load progress")
    parser.add_argument("--web", action="store_true", help="Serve browser dashboard")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument(
        "--refresh", type=float, default=2.0, help="Terminal refresh seconds"
    )
    parser.add_argument("--no-browser", action="store_true")
    args = parser.parse_args()

    if args.web:
        run_web_server(args.host, args.port, not args.no_browser)
    else:
        try:
            terminal_dashboard(args.refresh)
        except KeyboardInterrupt:
            print("\nStopped watching.")


if __name__ == "__main__":
    main()
