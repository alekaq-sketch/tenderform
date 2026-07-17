"""
Шаг 2 пайплайна. На вход - сырой текст из extract_raw.py (любой структуры,
любого языка). На выход - список позиций в едином формате, независимо от
того, как выглядел исходный документ.

Почему LLM, а не регулярки/фиксированные колонки:
  правило "3-я колонка - это количество" ломается на каждом новом шаблоне
  (см. пример: в одном файле кол-во в колонке 5, в другом - в колонке 4,
  заголовки на казахском и русском вперемешку). LLM сопоставляет поля
  по смыслу заголовка, а не по номеру колонки - это как раз то место,
  где "жёсткий" код принципиально не масштабируется на разные площадки.

ВАЖНО - это НЕ автопилот. Возвращаемый JSON нужно показать человеку
на проверку перед тем, как его цифры попадут в расчёт прибыли. Модель
может ошибиться в редких/нетипичных документах не меньше человека.

Требует переменную окружения ANTHROPIC_API_KEY (или явный api_key).
"""
import json
import os

EXTRACTION_PROMPT = """Ниже - сырой текст технического задания/спецификации с портала
госзакупок. Найди в нём ТОЛЬКО реальные позиции товара (лоты для поставки) -
конкретные наименования с количеством и/или ценой. НЕ включай в items:
  - заголовки разделов, повторяющиеся заголовки таблицы (если таблица разбита
    на страницы), примечания и сноски;
  - строки "Итого"/"Всего"/промежуточные и общие итоги;
  - технические характеристики, условия поставки и прочий текст, не являющийся
    отдельной позицией со своим количеством/ценой.
Если сомневаешься, является ли строка позицией лота - включай её только если у
неё есть количество или цена; иначе пропусти.

Верни ТОЛЬКО JSON (без markdown, без пояснений) в следующем формате:

{
  "lot_name": "...",
  "items": [
    {
      "name": "...",
      "unit": "...",
      "qty": число,
      "unit_price": число или null (если цены нет в документе),
      "delivery_terms": "..." или null,
      "delivery_days": число или null
    }
  ]
}

Если в документе двуязычные заголовки (например, казахский/русский через "/") -
бери русский вариант названия. Если что-то не найдено - используй null, не выдумывай.

ТЕКСТ ДОКУМЕНТА:
"""


def extract_fields(raw_text: str, api_key: str | None = None) -> dict:
    import anthropic  # imported lazily - this feature is optional (see README)

    client = anthropic.Anthropic(api_key=api_key) if api_key else anthropic.Anthropic()
    response = client.messages.create(
        model="claude-opus-4-8",
        # 2000 could truncate the JSON reply itself on a tender with many
        # line items (each item costs ~40-60 tokens of output) - raised to
        # comfortably fit a few hundred items before json.loads() below
        # would ever hit a cut-off response.
        max_tokens=8000,
        thinking={"type": "adaptive"},
        output_config={"effort": "medium"},
        # 60000 here is just a hard safety ceiling, not the active limit -
        # app.py already caps raw_text at 50000 chars before it gets here.
        messages=[{"role": "user", "content": EXTRACTION_PROMPT + raw_text[:60000]}],
    )
    text = next(block.text for block in response.content if block.type == "text")
    text = text.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
    return json.loads(text)


if __name__ == "__main__":
    import sys
    from extract_raw import extract_any

    raw = extract_any(sys.argv[1])
    result = extract_fields(raw)
    print(json.dumps(result, ensure_ascii=False, indent=2))
