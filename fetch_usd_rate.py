"""
Курс USD/KZT с открытого API Нацбанка РК - вместо ручного ввода в K9.
Документация: https://nationalbank.kz/ru/exchangerates/ezhednevnye-oficialnye-rynochnye-kursy-valyut
"""
import requests
from datetime import date


def get_usd_rate(on_date: str | None = None) -> float:
    """on_date в формате 'дд.мм.гггг'. Без даты - курс на сегодня."""
    d = on_date or date.today().strftime("%d.%m.%Y")
    url = f"https://www.nationalbank.kz/rss/get_rates.cfm?fdate={d}"
    resp = requests.get(url, timeout=10)
    resp.raise_for_status()
    # ответ - простой XML со списком валют
    import xml.etree.ElementTree as ET
    root = ET.fromstring(resp.content)
    for item in root.findall("item"):
        if item.findtext("title") == "USD":
            return float(item.findtext("description"))
    raise ValueError("USD не найден в ответе НацБанка")


if __name__ == "__main__":
    print("Курс USD сегодня:", get_usd_rate())
