from __future__ import annotations

from collections.abc import Callable
from datetime import datetime
from datetime import timedelta

from sqlalchemy import BigInteger
from sqlalchemy import DateTime
from sqlalchemy import ForeignKey
from sqlalchemy import func
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column
from sqlalchemy.orm import relationship

from src.common.clock import get_moscow_time
from src.common.db import Base
from src.consumption.models import Nutrition
from src.consumption.models import NUTRITION_FIELDS


class Meal(Base):
    __tablename__ = "meals"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(BigInteger, index=True)
    text: Mapped[str]
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    products: Mapped[list[MealProduct]] = relationship(back_populates="meal", cascade="all, delete-orphan")


class MealProduct(Base):
    __tablename__ = "meal_products"

    id: Mapped[int] = mapped_column(primary_key=True)
    meal_id: Mapped[int] = mapped_column(ForeignKey("meals.id", ondelete="CASCADE"), index=True)
    name: Mapped[str]
    weight_grams: Mapped[float]
    energy: Mapped[float]
    protein: Mapped[float]
    fat: Mapped[float]
    carbohydrates: Mapped[float]

    meal: Mapped[Meal] = relationship(back_populates="products")


class MealRepository:
    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        clock: Callable[[], datetime] = get_moscow_time,
    ):
        self._session_factory = session_factory
        self._clock = clock

    async def append_meal(self, user_id: int, text: str, products: list[dict]) -> None:
        meal = Meal(
            user_id=user_id,
            text=text,
            created_at=self._clock(),
            products=[MealProduct(**product) for product in products],
        )
        async with self._session_factory() as session:
            session.add(meal)
            await session.commit()

    async def read_today_totals(self, user_id: int) -> Nutrition:
        start, end = self._today_range()
        totals = [func.coalesce(func.sum(getattr(MealProduct, field)), 0.0) for field in NUTRITION_FIELDS]
        stmt = (
            select(*totals)
            .join(Meal, MealProduct.meal_id == Meal.id)
            .where(Meal.user_id == user_id, Meal.created_at >= start, Meal.created_at < end)
        )
        async with self._session_factory() as session:
            row = (await session.execute(stmt)).one()
        return Nutrition(**dict(zip(NUTRITION_FIELDS, row, strict=True)))

    def _today_range(self) -> tuple[datetime, datetime]:
        start = self._clock().replace(hour=0, minute=0, second=0, microsecond=0)
        return start, start + timedelta(days=1)
