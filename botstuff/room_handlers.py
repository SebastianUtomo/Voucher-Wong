"""
Room booking conversation flow using ConversationHandler.

States:
  PICK_ROOM → PICK_DATE → PICK_START → PICK_END → CONFIRM
"""

import logging
from datetime import date, datetime, timedelta

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ContextTypes, ConversationHandler, CommandHandler, CallbackQueryHandler
)

from config import ROOMS, MAX_BOOKING_HOURS, ADVANCE_DAYS
from bot.db import (
    get_bookings_for_room, get_bookings_for_user,
    has_overlap, add_booking, delete_booking
)

logger = logging.getLogger(__name__)

# ── conversation states ───────────────────────────────────────────────────────

PICK_ROOM, PICK_DATE, PICK_START, PICK_END, CONFIRM = range(5)

# ── helpers ───────────────────────────────────────────────────────────────────

def _room_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(label, callback_data=f"room_{rid}")]
        for rid, label in ROOMS.items()
    ])

def _date_keyboard():
    today = date.today()
    buttons = []
    for i in range(ADVANCE_DAYS):
        d = today + timedelta(days=i)
        label = d.strftime("%a, %d %b") + (" (today)" if i == 0 else "")
        buttons.append([InlineKeyboardButton(label, callback_data=f"date_{d.isoformat()}")])
    buttons.append([InlineKeyboardButton("❌ Cancel", callback_data="room_cancel")])
    return InlineKeyboardMarkup(buttons)

def _hour_keyboard(prefix: str, min_hour=7, max_hour=23, exclude_before=None):
    """Inline keyboard with hourly options."""
    start = exclude_before if exclude_before else min_hour
    buttons = []
    row = []
    for h in range(start, max_hour + 1):
        t = f"{h:02d}:00"
        row.append(InlineKeyboardButton(t, callback_data=f"{prefix}_{t}"))
        if len(row) == 4:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)
    buttons.append([InlineKeyboardButton("❌ Cancel", callback_data="room_cancel")])
    return InlineKeyboardMarkup(buttons)

def _bookings_text(room_id: str, date_str: str) -> str:
    bookings = get_bookings_for_room(room_id, date_str)
    if not bookings:
        return "_No bookings yet for this day._"
    lines = []
    for b in bookings:
        lines.append(f"  • {b['start_time']}–{b['end_time']} — {b['user_name']}")
    return "\n".join(lines)

# ── /book entry ───────────────────────────────────────────────────────────────

async def cmd_book(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    await update.message.reply_text(
        "🏠 *Room Booking*\n\nWhich room would you like to book?",
        parse_mode="Markdown",
        reply_markup=_room_keyboard()
    )
    return PICK_ROOM

# ── step 1: room chosen ───────────────────────────────────────────────────────

async def picked_room(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    room_id = query.data.replace("room_", "")
    context.user_data["room_id"] = room_id

    await query.edit_message_text(
        f"*{ROOMS[room_id]}* — pick a date:",
        parse_mode="Markdown",
        reply_markup=_date_keyboard()
    )
    return PICK_DATE

# ── step 2: date chosen ───────────────────────────────────────────────────────

async def picked_date(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    date_str = query.data.replace("date_", "")
    context.user_data["date"] = date_str

    room_id = context.user_data["room_id"]
    existing = _bookings_text(room_id, date_str)

    await query.edit_message_text(
        f"*{ROOMS[room_id]}* on *{date_str}*\n\n"
        f"Existing bookings:\n{existing}\n\n"
        f"Pick a *start time*:",
        parse_mode="Markdown",
        reply_markup=_hour_keyboard("start")
    )
    return PICK_START

# ── step 3: start time chosen ─────────────────────────────────────────────────

async def picked_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    start_time = query.data.replace("start_", "")
    context.user_data["start_time"] = start_time

    start_hour = int(start_time.split(":")[0])
    max_end = min(start_hour + MAX_BOOKING_HOURS, 23)

    await query.edit_message_text(
        f"Start: *{start_time}*\n\nNow pick an *end time* (max {MAX_BOOKING_HOURS}h):",
        parse_mode="Markdown",
        reply_markup=_hour_keyboard("end", exclude_before=start_hour + 1, max_hour=max_end)
    )
    return PICK_END

# ── step 4: end time chosen → confirm ────────────────────────────────────────

async def picked_end(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    end_time = query.data.replace("end_", "")
    context.user_data["end_time"] = end_time

    ud = context.user_data
    room_id   = ud["room_id"]
    date_str  = ud["date"]
    start     = ud["start_time"]

    if has_overlap(room_id, date_str, start, end_time):
        await query.edit_message_text(
            "⚠️ That slot overlaps an existing booking. Use /book to try again.",
            parse_mode="Markdown"
        )
        return ConversationHandler.END

    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✅ Confirm", callback_data="confirm_yes"),
            InlineKeyboardButton("❌ Cancel",  callback_data="room_cancel"),
        ]
    ])
    await query.edit_message_text(
        f"*Booking summary*\n\n"
        f"Room:  {ROOMS[room_id]}\n"
        f"Date:  {date_str}\n"
        f"Time:  {start} – {end_time}\n\n"
        f"Confirm?",
        parse_mode="Markdown",
        reply_markup=keyboard
    )
    return CONFIRM

# ── step 5: confirmed ─────────────────────────────────────────────────────────

async def confirm_booking(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user = query.from_user
    ud   = context.user_data
    room_id  = ud["room_id"]
    date_str = ud["date"]
    start    = ud["start_time"]
    end      = ud["end_time"]
    user_name = user.first_name or user.username or "Resident"

    # double-check overlap (race condition guard)
    if has_overlap(room_id, date_str, start, end):
        await query.edit_message_text("⚠️ Someone just booked that slot. Use /book to try again.")
        return ConversationHandler.END

    booking_id = add_booking(room_id, str(user.id), user_name, date_str, start, end)
    await query.edit_message_text(
        f"✅ *Booked!*\n\n"
        f"{ROOMS[room_id]}\n"
        f"{date_str}  {start} – {end}\n\n"
        f"Booking ID: `#{booking_id}`\n"
        f"Use /mybookings to see all your bookings.",
        parse_mode="Markdown"
    )
    context.user_data.clear()
    return ConversationHandler.END

# ── cancel anywhere ───────────────────────────────────────────────────────────

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query:
        await query.answer()
        await query.edit_message_text("Booking cancelled.")
    else:
        await update.message.reply_text("Booking cancelled.")
    context.user_data.clear()
    return ConversationHandler.END

# ── /mybookings ───────────────────────────────────────────────────────────────

async def cmd_mybookings(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    bookings = get_bookings_for_user(user_id)

    if not bookings:
        await update.message.reply_text("You have no upcoming bookings.")
        return

    lines = ["📋 *Your upcoming bookings:*\n"]
    for b in bookings:
        lines.append(
            f"• *{ROOMS.get(b['room_id'], b['room_id'])}*  "
            f"{b['date']}  {b['start_time']}–{b['end_time']}  "
            f"_(ID #{b['id']})_"
        )
    lines.append("\nTo cancel one, use /cancel\\_booking")
    await update.message.reply_text("\n".join(lines), parse_mode="Markdown")

# ── /roomstatus ───────────────────────────────────────────────────────────────

async def cmd_roomstatus(update: Update, context: ContextTypes.DEFAULT_TYPE):
    today = date.today().isoformat()
    lines = [f"🏠 *Room bookings for today ({today})*\n"]
    for rid, label in ROOMS.items():
        lines.append(f"*{label}*")
        lines.append(_bookings_text(rid, today))
        lines.append("")
    await update.message.reply_text("\n".join(lines), parse_mode="Markdown")

# ── /cancel_booking ───────────────────────────────────────────────────────────

async def cmd_cancel_booking(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    bookings = get_bookings_for_user(user_id)

    if not bookings:
        await update.message.reply_text("You have no upcoming bookings to cancel.")
        return

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton(
            f"{ROOMS.get(b['room_id'], b['room_id'])} · {b['date']} {b['start_time']}–{b['end_time']}",
            callback_data=f"cancelbook_{b['id']}"
        )]
        for b in bookings
    ])
    await update.message.reply_text("Which booking do you want to cancel?", reply_markup=keyboard)

async def do_cancel_booking(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    booking_id = int(query.data.replace("cancelbook_", ""))
    user_id = str(query.from_user.id)

    if delete_booking(booking_id, user_id):
        await query.edit_message_text(f"✅ Booking #{booking_id} cancelled.")
    else:
        await query.edit_message_text("⚠️ Could not cancel — it may already be gone.")

# ── conversation handler (to be registered in wsgi.py) ───────────────────────

def build_book_conversation():
    return ConversationHandler(
        entry_points=[CommandHandler("book", cmd_book)],
        states={
            PICK_ROOM:  [CallbackQueryHandler(picked_room,  pattern="^room_(?!cancel)")],
            PICK_DATE:  [CallbackQueryHandler(picked_date,  pattern="^date_")],
            PICK_START: [CallbackQueryHandler(picked_start, pattern="^start_")],
            PICK_END:   [CallbackQueryHandler(picked_end,   pattern="^end_")],
            CONFIRM:    [CallbackQueryHandler(confirm_booking, pattern="^confirm_yes$")],
        },
        fallbacks=[
            CallbackQueryHandler(cancel, pattern="^room_cancel$"),
            CommandHandler("cancel", cancel),
        ],
        per_user=True,
        per_chat=True,
    )
