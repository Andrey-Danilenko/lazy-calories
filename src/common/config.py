import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class Settings:
    deepseek_api_key: str
    deepseek_base_url: str
    deepseek_model: str
    telegram_token: str
    database_url: str
    qdrant_path: str
    qdrant_url: str
    qdrant_collection: str
    embedding_model: str
    nutrition_score_threshold: float

    @classmethod
    def from_env(cls) -> Settings:
        return cls(
            deepseek_api_key=os.getenv("DEEPSEEK_API_KEY", ""),
            deepseek_base_url=os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com"),
            deepseek_model=os.getenv("DEEPSEEK_MODEL", "deepseek-chat"),
            telegram_token=os.getenv("TELEGRAM_BOT_TOKEN", ""),
            database_url=os.getenv("DATABASE_URL", "postgresql+asyncpg://lazy:lazy@localhost:5432/lazycalories"),
            qdrant_path=os.getenv("QDRANT_PATH", "stored_data/qdrant"),
            qdrant_url=os.getenv("QDRANT_URL", ""),
            qdrant_collection=os.getenv("QDRANT_COLLECTION", "food_products"),
            embedding_model=os.getenv("EMBEDDING_MODEL", "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"),
            nutrition_score_threshold=float(os.getenv("NUTRITION_SCORE_THRESHOLD", "0.82")),
        )


settings = Settings.from_env()
