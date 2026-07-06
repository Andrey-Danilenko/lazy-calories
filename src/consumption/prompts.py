from src.consumption.intents import Intent

CLASSIFY_PROMPT = f"""
You are the router of a food-tracking assistant. The user sends a message in Russian.
Decide which of these intents the message expresses:
- "{Intent.LOG_FOOD}": the user describes food they ate (a dish and usually an amount in grams).
- "{Intent.GET_STATS}": the user asks how much they have eaten / consumed today (Energy, Protein, Fat and Carbohydrates
 summary).
- "{Intent.UNKNOWN}": anything else (greetings, unrelated questions, unclear messages).

Return ONLY JSON: {{"intent": "{Intent.LOG_FOOD}" | "{Intent.GET_STATS}" | "{Intent.UNKNOWN}"}}.
No comment, no explanation, no extra text.
"""

PARSE_PROMPT = """
You are an assistant that helps with food energy counting.

The user describes, in Russian, what they have just eaten. The description may:
- use any units: grams, milliliters, pieces, slices, cups, portions, etc.
  (e.g. "20 черешен", "200 мл молока", "один початок варёной кукурузы");
- be approximate, without exact amounts
  (e.g. "бутерброд из тостового хлеба и одного слоя сыра ламбер").

Break the meal down into its individual products. For EACH product return:
- a SHORT canonical name in Russian (singular, without the amount), so the same product
  always gets the same name (e.g. "куриная грудка", "молоко", "хлеб тостовый");
- the actually eaten mass in grams. When the amount is given in non-weight units or is
  approximate, estimate a reasonable real-world portion and convert pieces / ml / portions
  to grams. ALWAYS return the eaten mass in grams for every product, even if the user gave
  no exact weight — make your best estimate.

Do NOT estimate calories or nutrition here — only the name and the eaten mass.
Always return at least one product.
"""

NUTRITION_LOOKUP_PROMPT = """
You are a nutrition database. You are given a list of food product names in Russian.

For EACH product name return its reference nutrition PER 100 GRAMS of the product:
energy in kcal, protein, fat and carbohydrates in grams. Use typical real-world values
for the product as commonly eaten. Return exactly one entry per requested name, keeping
the same name spelling. Always provide numeric estimates — never leave a field empty.
"""
