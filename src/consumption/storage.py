import json
import os
from collections.abc import Callable
from datetime import datetime

from src.common.clock import get_moscow_time
from src.consumption.models import empty_nutrition
from src.consumption.models import Nutrition
from src.consumption.models import sum_nutrition

STORED_DATA_DIR = "stored_data"


class MealRepository:
    def __init__(self, base_dir: str = STORED_DATA_DIR, clock: Callable[[], datetime] = get_moscow_time):
        self._base_dir = base_dir
        self._clock = clock

    def _user_dir(self, user_id: int) -> str:
        user_dir = os.path.join(self._base_dir, str(user_id))
        os.makedirs(user_dir, exist_ok=True)
        return user_dir

    def _today_file(self, user_id: int) -> str:
        date_str = self._clock().strftime("%Y-%m-%d")
        return os.path.join(self._user_dir(user_id), f"{date_str}.jsonl")

    @staticmethod
    def _meal_products(record: dict) -> list[dict]:
        if "products" in record:
            return record["products"]
        return []

    def append_meal(self, user_id: int, text: str, products: list[dict]) -> None:
        record = {
            "time": self._clock().strftime("%H:%M:%S"),
            "text": text,
            "products": products,
        }
        with open(self._today_file(user_id), "a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")

    def read_today_totals(self, user_id: int) -> Nutrition:
        today_file = self._today_file(user_id)
        if not os.path.exists(today_file):
            return empty_nutrition()

        products: list[dict] = []
        with open(today_file, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                products.extend(self._meal_products(json.loads(line)))

        return sum_nutrition(products)
