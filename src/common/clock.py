from datetime import datetime

import pytz

MOSCOW_TZ = pytz.timezone("Europe/Moscow")


def get_moscow_time() -> datetime:
    return datetime.now(MOSCOW_TZ)
