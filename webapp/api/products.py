import os
import sys
import json
from http.server import BaseHTTPRequestHandler

current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

from dotenv import load_dotenv
load_dotenv(os.path.join(parent_dir, ".env"))

import cart

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        prods = cart._load_products()
        self.send_response(200)
        self.send_header('Content-type', 'application/json; charset=utf-8')
        self.end_headers()
        self.wfile.write(json.dumps(prods, ensure_ascii=False).encode('utf-8'))
