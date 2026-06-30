import os

from src.common.clock import get_moscow_time

LOGS_DIR = "logs"
os.makedirs(LOGS_DIR, exist_ok=True)


def get_username(user):
    if user.username:
        return f"@{user.username}"
    return f"user_{user.id}"


def log_user(update):
    date_str = get_moscow_time().strftime("%Y-%m-%d")
    user = update.effective_user

    users_file = os.path.join(LOGS_DIR, f"users_{date_str}.txt")

    existing_users = set()
    if os.path.exists(users_file):
        with open(users_file, encoding="utf-8") as f:
            existing_users = {line.strip().split(";")[0] for line in f}

    if str(user.id) not in existing_users:
        with open(users_file, "a", encoding="utf-8") as f:
            f.write(f"{user.id};{user.username};{user.first_name};{user.last_name}\n")


def log_action(update, action_description):
    moscow_now = get_moscow_time()
    date_str = moscow_now.strftime("%Y-%m-%d")
    time_str = moscow_now.strftime("%H:%M:%S")
    username = get_username(update.effective_user)

    log_file = os.path.join(LOGS_DIR, f"log_{date_str}.txt")
    log_entry = f"[{time_str}] {username}: {action_description}\n"

    with open(log_file, "a", encoding="utf-8") as f:
        f.write(log_entry)

    log_user(update)
