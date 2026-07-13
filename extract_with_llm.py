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

Требует переменную окружения ANTHROPIC_API_KEY.
"""
import json
import os
import requests

EXTRACTION_PROMPT = """Ниже - сырой текст технического задания/спецификации с портала
госзакупок. Найди в нём таблицу позиций товара и верни ТОЛЬКО JSON (без markdown,
без пояснений) в следующем формате:

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
    api_key = api_key or os.environ["ANTHROPIC_API_KEY"]
    resp = requests.post(
        "https://api.anthropic.com/v1/messages",
        headers={
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        },
        json={
            "model": "claude-sonnet-4-6",
            "max_tokens": 2000,
            "messages": [{"role": "user", "content": EXTRACTION_PROMPT + raw_text[:15000]}],
        },
        timeout=60,
    )
    resp.raise_for_status()
    text = resp.json()["content"][0]["text"]
    text = text.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
    return json.loads(text)


if __name__ == "__main__":
    import sys
    from extract_raw import extract_any

    raw = extract_any(sys.argv[1])
    result = extract_fields(raw)
    print(json.dumps(result, ensure_ascii=False, indent=2))
