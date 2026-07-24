import os
import sys
import json
from urllib.parse import parse_qs, urlparse
from http.server import BaseHTTPRequestHandler

current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

import bonuses

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        query = parse_qs(urlparse(self.path).query)
        user_id = query.get("user_id", [""])[0]
        val = bonuses.get_user_bonuses(user_id)
        self.send_response(200)
        self.send_header('Content-type', 'application/json; charset=utf-8')
        self.end_headers()
        self.wfile.write(json.dumps({"bonuses": val}).encode('utf-8'))
