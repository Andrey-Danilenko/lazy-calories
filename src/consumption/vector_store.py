import asyncio
import logging
import uuid

from qdrant_client import models
from qdrant_client import QdrantClient

from src.common.config import settings
from src.consumption.models import NUTRITION_FIELDS
from src.consumption.models import ProductNutrition

logger = logging.getLogger(__name__)

# Fixed namespace so the same product name always maps to the same point id (dedup on upsert).
_NAMESPACE = uuid.UUID("6f9619ff-8b86-d011-b42d-00cf4fc964ff")


class FoodVectorStore:
    """Per-100g nutrition cache backed by Qdrant + fastembed embeddings.

    Products are looked up by name; the LLM only fills misses, which are then cached here.
    """

    def __init__(self):
        self._collection = settings.qdrant_collection
        self._threshold = settings.nutrition_score_threshold
        self._model = settings.embedding_model
        if settings.qdrant_url:
            self._client = QdrantClient(url=settings.qdrant_url)
        else:
            self._client = QdrantClient(path=settings.qdrant_path)
        self._ensure_collection()

    def _ensure_collection(self) -> None:
        if not self._client.collection_exists(self._collection):
            self._client.create_collection(
                collection_name=self._collection,
                vectors_config=models.VectorParams(
                    size=self._client.get_embedding_size(self._model),
                    distance=models.Distance.COSINE,
                ),
            )

    def _document(self, name: str) -> models.Document:
        return models.Document(text=name, model=self._model)

    async def search(self, name: str) -> ProductNutrition | None:
        return await asyncio.to_thread(self._search, name)

    async def upsert(self, items: list[ProductNutrition]) -> None:
        if items:
            await asyncio.to_thread(self._upsert, items)

    def _search(self, name: str) -> ProductNutrition | None:
        hits = self._client.query_points(
            collection_name=self._collection,
            query=self._document(name),
            limit=1,
            score_threshold=self._threshold,
        ).points
        if not hits:
            return None
        return ProductNutrition(**hits[0].payload)

    def _upsert(self, items: list[ProductNutrition]) -> None:
        self._client.upsert(
            collection_name=self._collection,
            points=[
                models.PointStruct(
                    id=str(uuid.uuid5(_NAMESPACE, item.name)),
                    vector=self._document(item.name),
                    payload=self._payload(item),
                )
                for item in items
            ],
        )

    @staticmethod
    def _payload(item: ProductNutrition) -> dict:
        return {"name": item.name, **{field: getattr(item, field) for field in NUTRITION_FIELDS}}
