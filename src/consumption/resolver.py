from src.consumption.agent import ConsumptionAgent
from src.consumption.models import ProductNutrition
from src.consumption.models import scale_to_eaten
from src.consumption.vector_store import FoodVectorStore


class NutritionResolver:
    """Turns a free-text meal into scaled products, using the vector cache before the LLM.

    Flow: parse the message into named items, look each one up in the vector store, ask the
    LLM only for the misses (one batched call), cache the new references, then scale every
    per-100g reference to the eaten weight.
    """

    def __init__(self, agent: ConsumptionAgent, store: FoodVectorStore):
        self._agent = agent
        self._store = store

    async def resolve(self, message: str) -> list[dict]:
        items = (await self._agent.parse_meal(message)).items
        if not items:
            return []

        references = await self._collect_references(items)
        return [scale_to_eaten(references[item.name], item.weight_grams).model_dump() for item in items]

    async def _collect_references(self, items) -> dict[str, ProductNutrition]:
        references: dict[str, ProductNutrition] = {}
        misses: list[str] = []
        for name in dict.fromkeys(item.name for item in items):
            cached = await self._store.search(name)
            if cached is None:
                misses.append(name)
            else:
                references[name] = cached

        if misses:
            references.update(await self._resolve_misses(misses))
        return references

    async def _resolve_misses(self, names: list[str]) -> dict[str, ProductNutrition]:
        looked_up = (await self._agent.lookup_nutrition(names)).products
        by_name = {product.name: product for product in looked_up}
        resolved = {name: by_name.get(name) or looked_up[index] for index, name in enumerate(names)}
        await self._store.upsert(list(resolved.values()))
        return resolved
