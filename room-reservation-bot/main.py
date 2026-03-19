import logging
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ConversationHandler

from bot.config import BOT_TOKEN
from bot.handlers import (
    start,
    list_rooms,
    reserve_start,
    reserve_room_chosen,
    reserve_date_chosen,
    reserve_start_time_chosen,
    reserve_end_time_chosen,
    reserve_confirm,
    cancel_reservation_start,
    cancel_reservation_chosen,
    my_reservations,
    admin_add_room,
    admin_remove_room,
    admin_list_reservations,
    cancel_conv,
)
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

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


def main() -> None:
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    # --- Reserve conversation ---
    reserve_conv = ConversationHandler(
        entry_points=[CommandHandler("reserve", reserve_start)],
        states={
            CHOOSE_ROOM: [CallbackQueryHandler(reserve_room_chosen)],
            CHOOSE_DATE: [MessageHandler(filters.TEXT & ~filters.COMMAND, reserve_date_chosen)],
            CHOOSE_START_TIME: [MessageHandler(filters.TEXT & ~filters.COMMAND, reserve_start_time_chosen)],
            CHOOSE_END_TIME: [MessageHandler(filters.TEXT & ~filters.COMMAND, reserve_end_time_chosen)],
            CONFIRM: [CallbackQueryHandler(reserve_confirm)],
        },
        fallbacks=[CommandHandler("cancel", cancel_conv)],
    )

    # --- Cancel reservation conversation ---
    cancel_conv_handler = ConversationHandler(
        entry_points=[CommandHandler("cancel_reservation", cancel_reservation_start)],
        states={
            CANCEL_CHOOSE: [CallbackQueryHandler(cancel_reservation_chosen)],
        },
        fallbacks=[CommandHandler("cancel", cancel_conv)],
    )

    # --- Admin: add room conversation ---
    admin_add_conv = ConversationHandler(
        entry_points=[CommandHandler("admin_add_room", admin_add_room)],
        states={
            ADMIN_ROOM_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, admin_add_room)],
        },
        fallbacks=[CommandHandler("cancel", cancel_conv)],
    )

    # --- Admin: remove room conversation ---
    admin_remove_conv = ConversationHandler(
        entry_points=[CommandHandler("admin_remove_room", admin_remove_room)],
        states={
            ADMIN_REMOVE_CHOOSE: [CallbackQueryHandler(admin_remove_room)],
        },
        fallbacks=[CommandHandler("cancel", cancel_conv)],
    )

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("rooms", list_rooms))
    app.add_handler(CommandHandler("my_reservations", my_reservations))
    app.add_handler(CommandHandler("admin_reservations", admin_list_reservations))
    app.add_handler(reserve_conv)
    app.add_handler(cancel_conv_handler)
    app.add_handler(admin_add_conv)
    app.add_handler(admin_remove_conv)

    logger.info("Bot is running...")
    app.run_polling()


if __name__ == "__main__":
    main()
