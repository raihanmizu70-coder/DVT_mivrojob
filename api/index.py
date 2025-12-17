# api/index.py - Serverless Function for Render
from http.server import BaseHTTPRequestHandler
import json
import os
import sys
import psycopg2
from psycopg2.extras import RealDictCursor
import cloudinary
import cloudinary.uploader

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/api/health':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps({"status": "healthy"}).encode())
            return
        
        elif self.path == '/api/tasks':
            # Connect to database
            DATABASE_URL = os.getenv("DATABASE_URL")
            conn = psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)
            cur = conn.cursor()
            cur.execute("SELECT * FROM micro_jobs WHERE status='active'")
            tasks = cur.fetchall()
            cur.close()
            conn.close()
            
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps(tasks).encode())
            return
        
        else:
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({"message": "DVT API"}).encode())

    def do_POST(self):
        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length)
        data = json.loads(post_data.decode('utf-8'))
        
        if self.path == '/api/user':
            # Handle user registration
            telegram_id = data.get('telegram_id')
            
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            response = {"success": True, "user_id": telegram_id}
            self.wfile.write(json.dumps(response).encode())
            return
