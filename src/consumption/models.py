from typing import TypedDict

from pydantic import BaseModel
from pydantic import Field


class Product(BaseModel):
    name: str = Field(..., description="Short name of the eaten product or dish, in Russian")
    weight_grams: float = Field(..., description="Estimated eaten mass in grams (always provide an estimate)")
    energy: float = Field(..., description="Food energy in kcal for the eaten amount")
    protein: float = Field(..., description="Protein in grams for the eaten amount")
    fat: float = Field(..., description="Fat in grams for the eaten amount")
    carbohydrates: float = Field(..., description="Carbohydrates in grams for the eaten amount")


class Meal(BaseModel):
    products: list[Product] = Field(..., description="One entry per distinct product in the meal")


class Nutrition(TypedDict):
    energy: float  # food energy in kcal
    protein: float  # protein in grams
    fat: float  # fat in grams
    carbohydrates: float  # carbohydrates in grams


NUTRITION_FIELDS: tuple[str, ...] = ("energy", "protein", "fat", "carbohydrates")


def empty_nutrition() -> Nutrition:
    return dict.fromkeys(NUTRITION_FIELDS, 0.0)


def sum_nutrition(items: list[dict]) -> Nutrition:
    totals = empty_nutrition()
    for item in items:
        for field in NUTRITION_FIELDS:
            totals[field] += float(item.get(field, 0.0))
    return totals


def is_empty_nutrition(nutrition: Nutrition) -> bool:
    return all(nutrition[field] == 0 for field in NUTRITION_FIELDS)
