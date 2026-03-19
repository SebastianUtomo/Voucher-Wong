from datetime import datetime
from config import MACHINES
from bot.db import all_machines


def status_emoji(status: str) -> str:
    return {"free": "🟢", "in_use": "🔴", "done": "🟡"}.get(status, "⚪")


def machine_summary(row: dict) -> str:
    mid = row["machine_id"]
    machine = MACHINES[mid]
    status = row["status"]
    emoji = status_emoji(status)

    if status == "free":
        return f"{emoji} *{machine['name']}* — Available"
    elif status == "in_use":
        end = row.get("end_time")
        end_str = datetime.fromisoformat(end).strftime("%H:%M") if end else "?"
        return f"{emoji} *{machine['name']}* — In use by {row['user_name']} (done ~{end_str})"
    elif status == "done":
        return f"{emoji} *{machine['name']}* — Done, waiting for {row['user_name']} to collect"
    return f"{emoji} *{machine['name']}* — Unknown"


def all_status_text() -> str:
    rows = {r["machine_id"]: r for r in all_machines()}
    lines = ["🏠 *Laundry Room Status*\n"]

    lines.append("*— Washers —*")
    for mid in MACHINES:
        if MACHINES[mid]["type"] == "washer":
            lines.append(machine_summary(rows[mid]))

    lines.append("\n*— Dryers —*")
    for mid in MACHINES:
        if MACHINES[mid]["type"] == "dryer":
            lines.append(machine_summary(rows[mid]))

    lines.append(f"\n_Updated: {datetime.now().strftime('%H:%M:%S')}_")
    return "\n".join(lines)
