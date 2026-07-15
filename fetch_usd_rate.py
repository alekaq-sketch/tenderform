"""
Курсы валют с открытого API Нацбанка РК - вместо ручного ввода курса в форму.
Документация: https://nationalbank.kz/ru/exchangerates/ezhednevnye-oficialnye-rynochnye-kursy-valyut

Эндпоинт отдаёт ОДИН и тот же XML со списком всех валют на дату - мы просто
берём из него нужный код (USD/RUB/EUR/...), а не только доллар.
"""
import requests
from datetime import date

# Страна происхождения товара -> валюта закупки. Пополняйте по мере надобности.
COUNTRY_CURRENCY = {
    "китай": "USD",
    "гонконг": "USD",
    "оаэ": "USD",
    "турция": "USD",
    "россия": "RUB",
    "беларусь": "RUB",
    "германия": "EUR",
    "франция": "EUR",
    "италия": "EUR",
    "испания": "EUR",
    "польша": "EUR",
    "евросоюз": "EUR",
    "европа": "EUR",
}


def currency_for_country(country: str) -> str:
    """Подбирает валюту закупки по стране происхождения. По умолчанию USD -
    самая частая валюта внешнеторговых контрактов, если страна не распознана."""
    key = (country or "").strip().lower()
    for name, currency in COUNTRY_CURRENCY.items():
        if name in key:
            return currency
    return "USD"


def get_rate(currency: str, on_date: str | None = None) -> float:
    """currency - 'USD' / 'RUB' / 'EUR' и т.п. on_date в формате 'дд.мм.гггг'.
    Без даты - курс на сегодня."""
    currency = currency.strip().upper()
    d = on_date or date.today().strftime("%d.%m.%Y")
    url = f"https://www.nationalbank.kz/rss/get_rates.cfm?fdate={d}"
    resp = requests.get(url, timeout=10)
    resp.raise_for_status()
    # ответ - простой XML со списком валют
    import xml.etree.ElementTree as ET
    root = ET.fromstring(resp.content)
    for item in root.findall("item"):
        if item.findtext("title") == currency:
            return float(item.findtext("description"))
    raise ValueError(f"{currency} не найден в ответе НацБанка")


def get_usd_rate(on_date: str | None = None) -> float:
    """Оставлено для обратной совместимости со старым кодом, вызывающим
    именно эту функцию."""
    return get_rate("USD", on_date)


if __name__ == "__main__":
    for cur in ("USD", "RUB", "EUR"):
        print(f"Курс {cur} сегодня:", get_rate(cur))
