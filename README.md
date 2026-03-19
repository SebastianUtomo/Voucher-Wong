# building-bot

Telegram bot for apartment buildings — laundry machine tracking and room bookings.

## Features

**Laundry**
- See which washers/dryers are free
- Claim a machine and get a reminder before it finishes
- Auto-marks cycle as done and notifies you to collect

**Room Booking**
- Book the gym, BBQ pit, function room (or whatever you configure)
- Custom start/end times with overlap prevention
- See who has booked a room today
- Cancel your own bookings

## Setup

### 1. Create your bot
Message [@BotFather](https://t.me/BotFather) on Telegram and run `/newbot`. Copy the token.

### 2. Configure
Edit `config.py` — fill in `BOT_TOKEN`, `USERNAME`, and adjust `ROOMS` / `MACHINES` to match your building.

### 3. Install dependencies
```bash
pip install --user -r requirements.txt
```

### 4. Deploy to PythonAnywhere
- Upload this folder to `/home/yourusername/building-bot`
- Go to **Web** tab → add a new web app → Manual config → Python 3.10
- Set source/working directory to `/home/yourusername/building-bot`
- Paste the contents of `wsgi.py` into the WSGI config editor
- Hit **Reload**

## Commands

| Command | Description |
|---|---|
| `/status` | Laundry machine availability |
| `/use` | Start a machine |
| `/done` | Free up your machine |
| `/book` | Book a room |
| `/roomstatus` | Today's room bookings |
| `/mybookings` | Your upcoming bookings |
| `/cancel_booking` | Cancel a booking |
