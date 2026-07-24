import os
import sys
import json
from http.server import BaseHTTPRequestHandler

current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

import categories

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        cats = categories.load_categories()
        self.send_response(200)
        self.send_header('Content-type', 'application/json; charset=utf-8')
        self.end_headers()
        self.wfile.write(json.dumps(cats, ensure_ascii=False).encode('utf-8'))
