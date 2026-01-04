#!/usr/bin/env python3
"""
Simple HTTP server for documentation site
Handles CORS for local development
"""

import http.server
import socketserver
from functools import partial

PORT = 8080

class CORSRequestHandler(http.server.SimpleHTTPRequestHandler):
    def end_headers(self):
        # Add CORS headers
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.send_header('Cache-Control', 'no-store, no-cache, must-revalidate')
        return super().end_headers()

    def do_OPTIONS(self):
        self.send_response(200)
        self.end_headers()

if __name__ == '__main__':
    handler = CORSRequestHandler
    
    with socketserver.TCPServer(("", PORT), handler) as httpd:
        print(f"""
╔══════════════════════════════════════════════╗
║   DeltaStream Documentation Server           ║
╠══════════════════════════════════════════════╣
║                                              ║
║   Server running at:                         ║
║   http://localhost:{PORT}                      ║
║                                              ║
║   Press Ctrl+C to stop                       ║
║                                              ║
╚══════════════════════════════════════════════╝
        """)
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\n\nServer stopped.")
