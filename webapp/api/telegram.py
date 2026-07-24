import os
import sys
import json
import asyncio
from http.server import BaseHTTPRequestHandler

# Set correct sys.path for Vercel
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

from dotenv import load_dotenv
load_dotenv(os.path.join(parent_dir, ".env"))

import aiogram
from aiogram import Bot
from aiogram.types import Update

BOT_TOKEN = os.getenv("BOT_TOKEN")

from main import dp


async def process_telegram_update(update_data):
    # Create fresh bot instance per request to avoid closed event loop session reuse
    bot = Bot(token=BOT_TOKEN)
    try:
        update = Update.model_validate(update_data, context={"bot": bot})
        await dp.feed_update(bot, update)
    finally:
        await bot.session.close()


class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        content_length = int(self.headers.get('Content-Length', 0))
        post_data = self.rfile.read(content_length)
        
        try:
            update_data = json.loads(post_data.decode('utf-8'))
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                loop.run_until_complete(process_telegram_update(update_data))
            finally:
                loop.close()

            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({"status": "ok"}).encode('utf-8'))
        except Exception as e:
            print(f"[Vercel Webhook Exception]: {e}")
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({"status": "error", "message": str(e)}).encode('utf-8'))

    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/plain; charset=utf-8')
        self.end_headers()
        self.wfile.write("Telegram Bot Serverless Webhook is Active on Vercel 🚀".encode('utf-8'))
