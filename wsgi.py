import sys
import asyncio
import logging

from flask import Flask, request
from telegram import Update
from telegram.ext import Application, CommandHandler, CallbackQueryHandler

sys.path.insert(0, '/home/yourusername/laundry-bot')  # 👈 change yourusername

from config import BOT_TOKEN, WEBHOOK_URL
from bot.db import init_db
from bot.scheduler import scheduler
from bot.handlers import cmd_start, cmd_help, cmd_status, cmd_use, cmd_done, handle_callback
from bot.room_handlers import (
    build_book_conversation,
    cmd_mybookings, cmd_roomstatus, cmd_cancel_booking, do_cancel_booking
)

logging.basicConfig(
    format="%(asctime)s %(name)s %(levelname)s %(message)s",
    level=logging.INFO
)

# ── build telegram app ────────────────────────────────────────────────────────

tg_app = (
    Application.builder()
    .token(BOT_TOKEN)
    .updater(None)
    .build()
)

# laundry
tg_app.add_handler(CommandHandler("start",  cmd_start))
tg_app.add_handler(CommandHandler("help",   cmd_help))
tg_app.add_handler(CommandHandler("status", cmd_status))
tg_app.add_handler(CommandHandler("use",    cmd_use))
tg_app.add_handler(CommandHandler("done",   cmd_done))
tg_app.add_handler(CallbackQueryHandler(handle_callback, pattern="^(use|done)_"))

# room booking (ConversationHandler must be added before loose CallbackQueryHandlers)
tg_app.add_handler(build_book_conversation())
tg_app.add_handler(CommandHandler("mybookings",     cmd_mybookings))
tg_app.add_handler(CommandHandler("roomstatus",     cmd_roomstatus))
tg_app.add_handler(CommandHandler("cancel_booking", cmd_cancel_booking))
tg_app.add_handler(CallbackQueryHandler(do_cancel_booking, pattern="^cancelbook_"))

# ── startup ───────────────────────────────────────────────────────────────────

async def startup():
    init_db()
    await tg_app.initialize()
    await tg_app.bot.set_webhook(WEBHOOK_URL)
    scheduler.start()

asyncio.get_event_loop().run_until_complete(startup())

# ── flask ─────────────────────────────────────────────────────────────────────

flask_app = Flask(__name__)

@flask_app.route('/webhook', methods=['POST'])
def webhook():
    data = request.get_json(force=True)
    update = Update.de_json(data, tg_app.bot)
    asyncio.get_event_loop().run_until_complete(tg_app.process_update(update))
    return 'ok', 200

@flask_app.route('/')
def index():
    return '🤖 running', 200

application = flask_app
