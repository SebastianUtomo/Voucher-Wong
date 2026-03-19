from __future__ import annotations

import re
from datetime import date, datetime
from functools import wraps
from typing import Any

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler

from bot import db
from bot.config import ADMIN_IDS
from bot.states import (
    CHOOSE_ROOM,
    CHOOSE_DATE,
    CHOOSE_START_TIME,
    CHOOSE_END_TIME,
    CONFIRM,
    CANCEL_CHOOSE,
    ADMIN_ROOM_NAME,
    ADMIN_REMOVE_CHOOSE,
)

DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
TIME_RE = re.compile(r"^\d{2}:\d{2}$")


# ── Decorators ────────────────────────────────────────────────────────────────

def admin_only(func):
    @wraps(func)
    async def wrapper(update: Update, ctx: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        user = update.effective_user
        if user.id not in ADMIN_IDS:
            await update.effective_message.reply_text("⛔ Admin access only.")
            return ConversationHandler.END
        return await func(update, ctx, *args, **kwargs)
    return wrapper


# ── Helpers ───────────────────────────────────────────────────────────────────

def rooms_keyboard(rooms: list[db.Room]) -> InlineKeyboardMarkup:
    buttons = [
        [InlineKeyboardButton(r.name, callback_data=f"room:{r.id}")]
        for r in rooms
    ]
    return InlineKeyboardMarkup(buttons)


def reservation_summary(ctx: dict) -> str:
    return (
        f"📋 *Reservation Summary*\n"
        f"🏠 Room: {ctx['room_name']}\n"
        f"📅 Date: {ctx['date']}\n"
        f"🕐 Time: {ctx['start_time']} → {ctx['end_time']}"
    )


# ── Basic commands ────────────────────────────────────────────────────────────

async def start(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    name = update.effective_user.first_name
    await update.message.reply_text(
        f"👋 Hello, {name}! Welcome to the Room Reservation Bot.\n\n"
        "Available commands:\n"
        "  /rooms — list all rooms\n"
        "  /reserve — make a reservation\n"
        "  /my_reservations — view your upcoming reservations\n"
        "  /cancel_reservation — cancel one of your reservations\n\n"
        "Admin commands:\n"
        "  /admin_add_room — add a new room\n"
        "  /admin_remove_room — remove a room\n"
        "  /admin_reservations — view all reservations"
    )


async def list_rooms(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    rooms = db.get_all_rooms()
    if not rooms:
        await update.message.reply_text("No rooms available yet.")
        return
    lines = [f"🏠 *{r.name}*\n  _{r.description}_" for r in rooms]
    await update.message.reply_text("\n\n".join(lines), parse_mode="Markdown")


async def my_reservations(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    reservations = db.get_user_reservations(update.effective_user.id)
    if not reservations:
        await update.message.reply_text("You have no upcoming reservations.")
        return
    lines = []
    for r in reservations:
        lines.append(
            f"🔖 *#{r.id}* — {r.room_name}\n"
            f"   📅 {r.date}  🕐 {r.start_time}–{r.end_time}"
        )
    await update.message.reply_text("\n\n".join(lines), parse_mode="Markdown")


# ── Reserve flow ──────────────────────────────────────────────────────────────

async def reserve_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
    rooms = db.get_all_rooms()
    if not rooms:
        await update.message.reply_text("No rooms are available to reserve.")
        return ConversationHandler.END
    ctx.user_data.clear()
    await update.message.reply_text(
        "Which room would you like to reserve?",
        reply_markup=rooms_keyboard(rooms),
    )
    return CHOOSE_ROOM


async def reserve_room_chosen(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    room_id = int(query.data.split(":")[1])
    room = db.get_room(room_id)
    if not room:
        await query.edit_message_text("Room not found. Please try /reserve again.")
        return ConversationHandler.END

    ctx.user_data["room_id"] = room.id
    ctx.user_data["room_name"] = room.name

    await query.edit_message_text(
        f"Great, you picked *{room.name}*.\n\n"
        "Please enter the *date* for your reservation (YYYY-MM-DD):",
        parse_mode="Markdown",
    )
    return CHOOSE_DATE


async def reserve_date_chosen(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
    text = update.message.text.strip()
    if not DATE_RE.match(text):
        await update.message.reply_text("❌ Invalid format. Please use YYYY-MM-DD:")
        return CHOOSE_DATE

    try:
        chosen = date.fromisoformat(text)
    except ValueError:
        await update.message.reply_text("❌ That date doesn't exist. Try again:")
        return CHOOSE_DATE

    if chosen < date.today():
        await update.message.reply_text("❌ You can't reserve in the past. Try again:")
        return CHOOSE_DATE

    ctx.user_data["date"] = text
    await update.message.reply_text(
        "Enter the *start time* of your reservation (HH:MM, 24-hour):",
        parse_mode="Markdown",
    )
    return CHOOSE_START_TIME


async def reserve_start_time_chosen(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
    text = update.message.text.strip()
    if not TIME_RE.match(text):
        await update.message.reply_text("❌ Invalid format. Use HH:MM (e.g. 09:00):")
        return CHOOSE_START_TIME

    ctx.user_data["start_time"] = text
    await update.message.reply_text(
        "Enter the *end time* of your reservation (HH:MM, 24-hour):",
        parse_mode="Markdown",
    )
    return CHOOSE_END_TIME


async def reserve_end_time_chosen(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
    text = update.message.text.strip()
    if not TIME_RE.match(text):
        await update.message.reply_text("❌ Invalid format. Use HH:MM (e.g. 17:00):")
        return CHOOSE_END_TIME

    start = ctx.user_data["start_time"]
    if text <= start:
        await update.message.reply_text("❌ End time must be after start time. Try again:")
        return CHOOSE_END_TIME

    ctx.user_data["end_time"] = text

    # Check availability
    if not db.is_slot_available(
        ctx.user_data["room_id"],
        ctx.user_data["date"],
        start,
        text,
    ):
        await update.message.reply_text(
            "❌ That slot is already taken. Please /reserve again with a different time."
        )
        return ConversationHandler.END

    confirm_kb = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✅ Confirm", callback_data="confirm:yes"),
            InlineKeyboardButton("❌ Cancel", callback_data="confirm:no"),
        ]
    ])
    await update.message.reply_text(
        reservation_summary(ctx.user_data),
        parse_mode="Markdown",
        reply_markup=confirm_kb,
    )
    return CONFIRM


async def reserve_confirm(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()

    if query.data == "confirm:no":
        await query.edit_message_text("Reservation cancelled. Use /reserve to start over.")
        return ConversationHandler.END

    user = update.effective_user
    res_id = db.create_reservation(
        room_id=ctx.user_data["room_id"],
        user_id=user.id,
        username=user.username or user.first_name,
        on_date=ctx.user_data["date"],
        start=ctx.user_data["start_time"],
        end=ctx.user_data["end_time"],
    )

    if res_id is None:
        await query.edit_message_text(
            "❌ Someone just booked that slot. Please /reserve again."
        )
    else:
        await query.edit_message_text(
            f"✅ Reservation *#{res_id}* confirmed!\n\n"
            + reservation_summary(ctx.user_data),
            parse_mode="Markdown",
        )

    return ConversationHandler.END


# ── Cancel reservation flow ───────────────────────────────────────────────────

async def cancel_reservation_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
    reservations = db.get_user_reservations(update.effective_user.id)
    if not reservations:
        await update.message.reply_text("You have no upcoming reservations to cancel.")
        return ConversationHandler.END

    buttons = [
        [InlineKeyboardButton(
            f"#{r.id} — {r.room_name} on {r.date} {r.start_time}–{r.end_time}",
            callback_data=f"cancel:{r.id}",
        )]
        for r in reservations
    ]
    await update.message.reply_text(
        "Which reservation would you like to cancel?",
        reply_markup=InlineKeyboardMarkup(buttons),
    )
    return CANCEL_CHOOSE


async def cancel_reservation_chosen(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    res_id = int(query.data.split(":")[1])

    success = db.cancel_reservation(res_id, update.effective_user.id)
    if success:
        await query.edit_message_text(f"✅ Reservation #{res_id} has been cancelled.")
    else:
        await query.edit_message_text("❌ Could not cancel that reservation.")
    return ConversationHandler.END


# ── Admin: view all reservations ──────────────────────────────────────────────

@admin_only
async def admin_list_reservations(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    reservations = db.get_all_reservations()
    if not reservations:
        await update.message.reply_text("No upcoming reservations.")
        return
    lines = []
    for r in reservations:
        lines.append(
            f"🔖 *#{r.id}* — {r.room_name}\n"
            f"   👤 @{r.username}  📅 {r.date}  🕐 {r.start_time}–{r.end_time}"
        )
    await update.message.reply_text("\n\n".join(lines), parse_mode="Markdown")


# ── Admin: add room ────────────────────────────────────────────────────────────

@admin_only
async def admin_add_room(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
    # Entry point
    if update.message and update.message.text == "/admin_add_room":
        await update.message.reply_text(
            "Send me the room details in this format:\n`Name | Description`",
            parse_mode="Markdown",
        )
        return ADMIN_ROOM_NAME

    # Receiving the room info
    text = update.message.text.strip()
    parts = [p.strip() for p in text.split("|", 1)]
    name = parts[0]
    description = parts[1] if len(parts) > 1 else ""

    if not name:
        await update.message.reply_text("❌ Room name cannot be empty. Try again:")
        return ADMIN_ROOM_NAME

    success = db.add_room(name, description)
    if success:
        await update.message.reply_text(f"✅ Room *{name}* added!", parse_mode="Markdown")
    else:
        await update.message.reply_text(f"❌ A room named *{name}* already exists.", parse_mode="Markdown")
    return ConversationHandler.END


# ── Admin: remove room ────────────────────────────────────────────────────────

@admin_only
async def admin_remove_room(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
    # Entry point
    if update.message and update.message.text == "/admin_remove_room":
        rooms = db.get_all_rooms()
        if not rooms:
            await update.message.reply_text("No rooms to remove.")
            return ConversationHandler.END
        await update.message.reply_text(
            "Which room do you want to remove?",
            reply_markup=rooms_keyboard(rooms),
        )
        return ADMIN_REMOVE_CHOOSE

    # Receiving callback
    query = update.callback_query
    await query.answer()
    room_id = int(query.data.split(":")[1])
    room = db.get_room(room_id)
    name = room.name if room else f"#{room_id}"
    success = db.remove_room(room_id)
    if success:
        await query.edit_message_text(f"✅ Room *{name}* removed.", parse_mode="Markdown")
    else:
        await query.edit_message_text("❌ Room not found.")
    return ConversationHandler.END


# ── Fallback ──────────────────────────────────────────────────────────────────

async def cancel_conv(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("Operation cancelled.")
    return ConversationHandler.END
