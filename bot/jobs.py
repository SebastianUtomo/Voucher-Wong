import logging
from datetime import datetime
from config import MACHINES, REMINDER_MINUTES
from bot.db import get_machine, set_machine

logger = logging.getLogger(__name__)


async def send_reminder(app, user_id: str, mid: str, end_time: datetime):
    try:
        await app.bot.send_message(
            chat_id=int(user_id),
            text=(
                f"⏰ *{MACHINES[mid]['name']}* finishes at *{end_time.strftime('%H:%M')}* "
                f"— {REMINDER_MINUTES} min to go! Get ready to collect. 👕"
            ),
            parse_mode="Markdown"
        )
    except Exception as e:
        logger.error(f"Reminder failed for {mid}: {e}")


async def mark_done(app, mid: str):
    row = get_machine(mid)
    user_id = row.get("user_id")
    set_machine(mid, "done", user_id, row.get("user_name"), row.get("end_time"))

    if user_id:
        try:
            await app.bot.send_message(
                chat_id=int(user_id),
                text=(
                    f"🔔 Your *{MACHINES[mid]['name']}* is done! "
                    f"Please collect your laundry and use /done to free the machine."
                ),
                parse_mode="Markdown"
            )
        except Exception as e:
            logger.error(f"Done notification failed for {mid}: {e}")
