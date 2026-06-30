from enum import StrEnum


class Intent(StrEnum):
    LOG_FOOD = "log_food"
    GET_STATS = "get_stats"
    UNKNOWN = "unknown"
