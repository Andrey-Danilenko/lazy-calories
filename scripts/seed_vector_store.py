"""Seed the Qdrant nutrition cache with reference products (per 100 g).

Run from the project root:

    uv run python scripts/seed_vector_store.py

Re-running is safe: each product name maps to a deterministic id, so existing
entries are overwritten instead of duplicated.

NOTE: with the default embedded Qdrant (QDRANT_PATH), the store is single-writer —
stop the bot before running this. To seed while the bot runs, use a Qdrant server
(set QDRANT_URL).
"""

import asyncio
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from src.consumption.models import ProductNutrition  # noqa: E402
from src.consumption.vector_store import FoodVectorStore  # noqa: E402

# Reference nutrition PER 100 g. Edit / extend this list freely.
PRODUCTS: list[ProductNutrition] = [
    ProductNutrition(name="куриная грудка", energy=113, protein=23.6, fat=1.9, carbohydrates=0.4),
    ProductNutrition(name="молоко", energy=60, protein=3.0, fat=3.2, carbohydrates=4.7),
    ProductNutrition(name="гречка отварная", energy=110, protein=4.2, fat=1.1, carbohydrates=21.3),
    ProductNutrition(name="яйцо куриное", energy=157, protein=12.7, fat=11.5, carbohydrates=0.7),
    ProductNutrition(name="банан", energy=89, protein=1.1, fat=0.3, carbohydrates=23.0),
]


async def main() -> None:
    store = FoodVectorStore()
    await store.upsert(PRODUCTS)
    print(f"Upserted {len(PRODUCTS)} products into the vector store")


if __name__ == "__main__":
    asyncio.run(main())
