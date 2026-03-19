USERNAME    = "yourusername"               # 👈 your PythonAnywhere username
BOT_TOKEN   = "YOUR_BOT_TOKEN_HERE"        # 👈 from @BotFather
WEBHOOK_URL = f"https://{USERNAME}.pythonanywhere.com/webhook"
DB_FILE     = f"/home/{USERNAME}/laundry-bot/laundry.db"

REMINDER_MINUTES = 5

MACHINES = {
    "washer_1": {"name": "Washer 1", "type": "washer", "duration_min": 45},
    "washer_2": {"name": "Washer 2", "type": "washer", "duration_min": 45},
    "dryer_1":  {"name": "Dryer 1",  "type": "dryer",  "duration_min": 60},
    "dryer_2":  {"name": "Dryer 2",  "type": "dryer",  "duration_min": 60},
}

# Rooms available for booking. Add/remove as needed.
ROOMS = {
    "gym":       "🏋️ Gym",
    "bbq":       "🍖 BBQ Pit",
    "function":  "🏛️ Function Room",
}

# Booking rules
MAX_BOOKING_HOURS = 4    # max duration per booking
ADVANCE_DAYS      = 7    # how many days ahead residents can book
