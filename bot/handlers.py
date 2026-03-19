import logging
from datetime import datetime, timedelta

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from config import MACHINES, REMINDER_MINUTES
from bot.db import get_machine, set_machine, all_machines
from bot.helpers import all_status_text
from bot.jobs import send_reminder, mark_done

logger = logging.getLogger(__name__)


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 *Building Bot*\n\n"
        "*🧺 Laundry*\n"
        "/status — see machine availability\n"
        "/use — start a machine\n"
        "/done — free up your machine\n\n"
        "*🏠 Room Booking*\n"
        "/book — book a room\n"
        "/roomstatus — today's room bookings\n"
        "/mybookings — your upcoming bookings\n"
        "/cancel\\_booking — cancel a booking\n\n"
        "/help — show this message",
        parse_mode="Markdown"
    )


async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await cmd_start(update, context)


async def cmd_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(all_status_text(), parse_mode="Markdown")


async def cmd_use(update: Update, context: ContextTypes.DEFAULT_TYPE):
    rows = {r["machine_id"]: r for r in all_machines()}
    free = [mid for mid in MACHINES if rows[mid]["status"] == "free"]

    if not free:
        await update.message.reply_text("😔 All machines are in use right now. Try again soon!")
        return

    keyboard = [
        [InlineKeyboardButton(
            f"{MACHINES[mid]['name']} ({MACHINES[mid]['duration_min']} min)",
            callback_data=f"use_{mid}"
        )]
        for mid in free
    ]
    await update.message.reply_text(
        "Which machine are you starting?",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def cmd_done(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    rows = {r["machine_id"]: r for r in all_machines()}
    mine = [
        mid for mid in MACHINES
        if str(rows[mid].get("user_id")) == user_id
        and rows[mid]["status"] in ("in_use", "done")
    ]

    if not mine:
        await update.message.reply_text("You don't have any active machines.")
        return

    keyboard = [
        [InlineKeyboardButton(MACHINES[mid]["name"], callback_data=f"done_{mid}")]
        for mid in mine
    ]
    await update.message.reply_text(
        "Which machine are you done with?",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    from bot.scheduler import scheduler

    query = update.callback_query
    await query.answer()
    action, mid = query.data.split("_", 1)
    user = query.from_user
    user_id = str(user.id)
    user_name = user.first_name or user.username or "Someone"

    if action == "use":
        row = get_machine(mid)
        if row["status"] != "free":
            await query.edit_message_text("⚠️ That machine was just taken. Try /use again.")
            return

        duration = MACHINES[mid]["duration_min"]
        end_time = datetime.now() + timedelta(minutes=duration)
        set_machine(mid, "in_use", user_id, user_name, end_time.isoformat())

        reminder_time = end_time - timedelta(minutes=REMINDER_MINUTES)
        if reminder_time > datetime.now():
            scheduler.add_job(
                send_reminder, "date", run_date=reminder_time,
                args=[context.application, user_id, mid, end_time],
                id=f"reminder_{mid}", replace_existing=True
            )
        scheduler.add_job(
            mark_done, "date", run_date=end_time,
            args=[context.application, mid],
            id=f"done_{mid}", replace_existing=True
        )

        await query.edit_message_text(
            f"✅ *{MACHINES[mid]['name']}* started!\n"
            f"⏱ Done around *{end_time.strftime('%H:%M')}*\n"
            f"I'll remind you {REMINDER_MINUTES} min before it finishes.",
            parse_mode="Markdown"
        )

    elif action == "done":
        row = get_machine(mid)
        if str(row.get("user_id")) != user_id:
            await query.edit_message_text("⚠️ That's not your machine.")
            return

        set_machine(mid, "free")
        for job_id in (f"reminder_{mid}", f"done_{mid}"):
            job = scheduler.get_job(job_id)
            if job:
                job.remove()

        await query.edit_message_text(f"👍 *{MACHINES[mid]['name']}* is now free!", parse_mode="Markdown")
