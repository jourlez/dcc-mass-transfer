#!/usr/bin/env python3
"""
Simple REST API for Mass Transfer
Run this to expose an HTTP endpoint for triggering mass transfers
"""

from http.server import HTTPServer, BaseHTTPRequestHandler
import json
import subprocess
import os
from datetime import datetime
from urllib.parse import parse_qs

PORT = 8080
SCRIPT_PATH = './mass_transfer_pywaves.py'
LOG_FILE = './api.log'

class MassTransferHandler(BaseHTTPRequestHandler):
    
    def log_message(self, format, *args):
        """Override to use custom logging"""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        message = f"[{timestamp}] {format % args}\n"
        with open(LOG_FILE, 'a') as f:
            f.write(message)
        print(message.strip())
    
    def _send_response(self, status, data):
        """Send JSON response"""
        self.send_response(status)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps(data, indent=2).encode())
    
    def do_GET(self):
        """Handle GET requests"""
        if self.path == '/':
            self._send_response(200, {
                'service': 'DecentralChain Mass Transfer API',
                'version': '1.0',
                'endpoints': {
                    'POST /transfer': 'Trigger mass transfer with CSV file path',
                    'GET /status': 'Check service status',
                    'GET /logs': 'View recent logs'
                }
            })
        
        elif self.path == '/status':
            self._send_response(200, {
                'status': 'online',
                'timestamp': datetime.now().isoformat(),
                'script': SCRIPT_PATH,
                'exists': os.path.exists(SCRIPT_PATH)
            })
        
        elif self.path == '/logs':
            try:
                with open(LOG_FILE, 'r') as f:
                    logs = f.readlines()[-50:]  # Last 50 lines
                
                self._send_response(200, {
                    'logs': logs,
                    'count': len(logs)
                })
            except Exception as e:
                self._send_response(500, {'error': str(e)})
        
        else:
            self._send_response(404, {'error': 'Endpoint not found'})
    
    def do_POST(self):
        """Handle POST requests"""
        if self.path == '/transfer':
            try:
                # Get request body
                content_length = int(self.headers.get('Content-Length', 0))
                body = self.rfile.read(content_length).decode()
                
                # Parse JSON or form data
                try:
                    data = json.loads(body)
                    csv_path = data.get('csv_file')
                except json.JSONDecodeError:
                    # Try form data
                    params = parse_qs(body)
                    csv_path = params.get('csv_file', [None])[0]
                
                if not csv_path:
                    self._send_response(400, {
                        'error': 'Missing csv_file parameter',
                        'example': '{"csv_file": "recipients.csv"}'
                    })
                    return
                
                if not os.path.exists(csv_path):
                    self._send_response(404, {
                        'error': f'CSV file not found: {csv_path}'
                    })
                    return
                
                # Run mass transfer script
                self.log_message(f"Executing mass transfer: {csv_path}")
                
                result = subprocess.run(
                    ['python3', SCRIPT_PATH, csv_path],
                    capture_output=True,
                    text=True,
                    timeout=300
                )
                
                if result.returncode == 0:
                    self._send_response(200, {
                        'status': 'success',
                        'csv_file': csv_path,
                        'output': result.stdout[-1000:],  # Last 1000 chars
                        'timestamp': datetime.now().isoformat()
                    })
                else:
                    self._send_response(500, {
                        'status': 'failed',
                        'csv_file': csv_path,
                        'error': result.stderr[-1000:],
                        'timestamp': datetime.now().isoformat()
                    })
            
            except subprocess.TimeoutExpired:
                self._send_response(504, {
                    'error': 'Script execution timed out (>5 minutes)'
                })
            
            except Exception as e:
                self._send_response(500, {
                    'error': str(e)
                })
        
        else:
            self._send_response(404, {'error': 'Endpoint not found'})
    
    def do_OPTIONS(self):
        """Handle CORS preflight"""
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()

def main():
    server = HTTPServer(('0.0.0.0', PORT), MassTransferHandler)
    
    print("=" * 60)
    print("DecentralChain Mass Transfer API")
    print("=" * 60)
    print(f"Server running on http://localhost:{PORT}")
    print(f"Log file: {LOG_FILE}")
    print("=" * 60)
    print("\nEndpoints:")
    print(f"  GET  http://localhost:{PORT}/")
    print(f"  GET  http://localhost:{PORT}/status")
    print(f"  GET  http://localhost:{PORT}/logs")
    print(f"  POST http://localhost:{PORT}/transfer")
    print("\nExample usage:")
    print(f'  curl -X POST http://localhost:{PORT}/transfer \\')
    print(f'    -H "Content-Type: application/json" \\')
    print(f'    -d \'{{"csv_file": "recipients.csv"}}\'')
    print("\nPress Ctrl+C to stop.\n")
    
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n\nShutting down...")
        server.shutdown()

if __name__ == '__main__':
    main()
