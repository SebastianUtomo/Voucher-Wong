# 🏠 Room Reservation Telegram Bot

A Telegram bot that lets users reserve rooms with date and time slots. Built with Python, [python-telegram-bot](https://python-telegram-bot.org/), and SQLite.

---

## ✨ Features

| Feature | Command |
|---|---|
| List all available rooms | `/rooms` |
| Reserve a room (date + time slot) | `/reserve` |
| View your upcoming reservations | `/my_reservations` |
| Cancel one of your reservations | `/cancel_reservation` |
| *(Admin)* Add a new room | `/admin_add_room` |
| *(Admin)* Remove a room | `/admin_remove_room` |
| *(Admin)* View all reservations | `/admin_reservations` |

- Conflict detection — double bookings are prevented automatically.
- Guided conversation flow with inline keyboard buttons.
- Admin access control via configurable user ID allow-list.

---

## 🗂 Project Structure

```
room-reservation-bot/
├── bot/
│   ├── __init__.py
│   ├── config.py       # Env-var loading
│   ├── db.py           # SQLite data layer
│   ├── handlers.py     # All Telegram handlers
│   ├── main.py         # Entry point & handler registration
│   └── states.py       # ConversationHandler state constants
├── data/               # Auto-created; holds reservations.db (git-ignored)
├── .env.example
├── .gitignore
├── docker-compose.yml
├── Dockerfile
└── requirements.txt
```

---

## 🚀 Quick Start

### 1. Create your bot

1. Open Telegram and message [@BotFather](https://t.me/BotFather).
2. Send `/newbot` and follow the prompts.
3. Copy the **token** you receive.

### 2. Clone and configure

```bash
git clone https://github.com/your-username/room-reservation-bot.git
cd room-reservation-bot

cp .env.example .env
# Edit .env and paste your token + admin Telegram user ID(s)
```

Find your Telegram user ID by messaging [@userinfobot](https://t.me/userinfobot).

### 3a. Run locally (Python)

```bash
python -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate
pip install -r requirements.txt

python -m bot.main
```

### 3b. Run with Docker

```bash
docker compose up -d
```

The SQLite database is persisted in a named Docker volume (`bot_data`).

---

## ⚙️ Configuration

| Variable | Required | Description |
|---|---|---|
| `BOT_TOKEN` | ✅ | Token from @BotFather |
| `ADMIN_IDS` | ❌ | Comma-separated Telegram user IDs for admin access |

---

## 📋 Usage Walkthrough

### Making a reservation

1. `/reserve` — bot shows all available rooms as buttons.
2. Tap a room.
3. Enter the date: `2025-08-20`
4. Enter start time: `09:00`
5. Enter end time: `11:00`
6. Confirm or cancel via the inline buttons.

### Cancelling a reservation

1. `/cancel_reservation` — bot lists your upcoming reservations.
2. Tap the one you want to remove.

### Admin: Adding a room

1. `/admin_add_room`
2. Send: `Room D | Small quiet room, capacity 2`

### Admin: Removing a room

1. `/admin_remove_room` — bot lists all rooms.
2. Tap the one to delete. All its reservations are deleted too (cascade).

---

## 🛡 Conflict Detection

The bot prevents overlapping reservations using this SQL check:

```sql
SELECT COUNT(*) FROM reservations
WHERE room_id = ?
  AND date = ?
  AND start_time < :end
  AND end_time > :start
```

If a slot is taken between the time you start the conversation and the time you confirm, you'll be notified and prompted to try again.

---

## 🐳 Deploying to a Server

```bash
# On your VPS / cloud instance
git clone https://github.com/your-username/room-reservation-bot.git
cd room-reservation-bot
cp .env.example .env && nano .env   # fill in values
docker compose up -d
docker compose logs -f              # watch logs
```

---

## 📄 License

MIT
