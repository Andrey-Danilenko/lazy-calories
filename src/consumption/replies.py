from src.consumption.models import Nutrition

FALLBACK_REPLY = (
    "Я помогаю считать КБЖУ. Напишите, что вы съели и сколько грамм "
    "(например: «съел 150 г гречки»), или спросите, сколько вы съели сегодня."
)

REJECTED_REPLY = "Извините, я не могу обработать это сообщение. Я помогаю только считать КБЖУ."

EXTRACTION_FAILED_REPLY = (
    "Не удалось распознать съеденное. Попробуйте описать иначе, например: «100 г гречки, 200 мл молока и одно яблоко»."
)

NO_STATS_REPLY = "Сегодня вы ещё ничего не записывали."


def format_nutrition(nutrition: Nutrition) -> str:
    return (
        f"🔥 Энергия: {nutrition['energy']:.0f} ккал\n"
        f"🥩 Белки: {nutrition['protein']:.1f} г\n"
        f"🧈 Жиры: {nutrition['fat']:.1f} г\n"
        f"🍞 Углеводы: {nutrition['carbohydrates']:.1f} г"
    )


def meal_logged(total: Nutrition) -> str:
    return "Записал! Этот приём пищи:\n" + format_nutrition(total)


def daily_stats(totals: Nutrition) -> str:
    return "Сегодня вы съели:\n" + format_nutrition(totals)
