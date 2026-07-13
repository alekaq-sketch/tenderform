"""
Заполняет шаблон "Аналитика.xlsx" данными по конкретному лоту,
не трогая формулы (только "входные" ячейки).
 
Карта входных ячеек в шаблоне (лист "расчет"):
    B2  - ФИО менеджера / закупщика
    B3  - Поставщик
    R2  - Номер лота
    B4  - Дата расчёта
    B5  - Дата начала лота
    B6  - Дата окончания лота
    B7  - Срок производства, дней
    J9  - Коэффициент наценки (например 1.5 = +50%)
    K9  - Курс USD
    C12 - Наименование товара
    D12 - Количество
    E12 - Цена закупки DDP (с НДС)
    H18 - Сумма дорожных расходов
 
Если позиций в лоте несколько - используйте fill_multi() ниже.
"""
import openpyxl
from datetime import date
from copy import copy
from openpyxl.cell.cell import MergedCell
from openpyxl.formula.translate import Translator
 
 
def autosize_columns(ws, min_width=8, max_width=60, padding=2):
    """
    openpyxl не умеет 'автоподбор ширины' как Excel (это расчёт на лету
    в самом Excel) - поэтому считаем сами: ширина колонки = длина самого
    длинного содержимого в ней + отступ, в разумных границах.
    """
    widths = {}
    for row in ws.iter_rows():
        for cell in row:
            if isinstance(cell, MergedCell) or cell.value is None:
                continue
            # многострочный текст (с переносами) - берём самую длинную строку
            length = max(len(line) for line in str(cell.value).split("\n"))
            widths[cell.column_letter] = max(widths.get(cell.column_letter, 0), length)
 
    for col, length in widths.items():
        ws.column_dimensions[col].width = min(max(length + padding, min_width), max_width)
 
 
def compose_item_name(item: dict) -> str:
    return item.get("item_name") or item.get("name") or ""
 
 
def fill_single(template_path: str, output_path: str, lot: dict):
    """lot - словарь с ключами из карты выше (см. пример в __main__)."""
    wb = openpyxl.load_workbook(template_path)  # без data_only! формулы должны остаться
    ws = wb["расчет"]
 
    ws["B2"] = lot["manager"]
    ws["B3"] = lot["supplier"]
    ws["R2"] = f'лот {lot["lot_number"]}'
    ws["B4"] = f'Дата:{lot["calc_date"]}'
    ws["B5"] = f'Дата начала лота:{lot["lot_start"]}'
    ws["B6"] = f'Дата окончания лота: {lot["lot_end"]}'
    ws["B7"] = f'Срок производства: {lot["lead_time_days"]} дн'
 
    ws["J9"] = lot["markup_coef"]
    ws["K9"] = lot["usd_rate"]
    ws["H18"] = lot.get("road_cost") or 0
 
    ws["C12"] = compose_item_name({"item_name": lot["item_name"]})
    ws["D12"] = lot["qty"]
    ws["E12"] = lot["purchase_price_ddp"]
 
    wb.save(output_path)
    print(f"Saved: {output_path}")
 
 
def fill_multi(template_path: str, output_path: str, header: dict, items: list[dict]):
    """
    Несколько позиций в одном лоте.
    header - те же поля, что в fill_single, кроме item_name/qty/purchase_price_ddp.
    items  - список {"item_name", "qty", "purchase_price_ddp"}.
    Копирует формулы строки 12 на строки 13..(12+len(items)-1) и сдвигает
    итоговую строку "Итого"/суммы вниз.
    """
    wb = openpyxl.load_workbook(template_path)
    ws = wb["расчет"]
 
    ws["B2"] = header["manager"]
    ws["B3"] = header["supplier"]
    ws["R2"] = f'лот {header["lot_number"]}'
    ws["B4"] = f'Дата:{header["calc_date"]}'
    ws["B5"] = f'Дата начала лота:{header["lot_start"]}'
    ws["B6"] = f'Дата окончания лота: {header["lot_end"]}'
    ws["B7"] = f'Срок производства: {header["lead_time_days"]} дн'
    ws["J9"] = header["markup_coef"]
    ws["K9"] = header["usd_rate"]
    ws["H18"] = header.get("road_cost") or 0
 
    first_row = 12
    # число дополнительных строк, кроме уже существующей 12-й
    extra = len(items) - 1
    if extra > 0:
        ws.insert_rows(first_row + 1, amount=extra)
        for r in range(first_row + 1, first_row + 1 + extra):
            for col in "ABCDEFGHJKLMNOPQRS":
                src = ws[f"{col}{first_row}"]
                dst = ws[f"{col}{r}"]
                if isinstance(src.value, str) and src.value.startswith("="):
                    dst.value = Translator(src.value, origin=src.coordinate).translate_formula(dst.coordinate)
                else:
                    dst.value = src.value
                if src.has_style:
                    dst._style = copy(src._style)
                if src.number_format:
                    dst.number_format = src.number_format
                if src.alignment:
                    dst.alignment = copy(src.alignment)
                if src.font:
                    dst.font = copy(src.font)
                if src.fill:
                    dst.fill = copy(src.fill)
                if src.border:
                    dst.border = copy(src.border)
 
    for i, item in enumerate(items):
        r = first_row + i
        ws[f"B{r}"] = i + 1
        ws[f"C{r}"] = compose_item_name(item)
        ws[f"D{r}"] = item["qty"]
        ws[f"E{r}"] = item["purchase_price_ddp"]
 
    # строка сумм (была 13) и все нижестоящие ссылки надо будет поправить вручную
    # при большом числе позиций - см. README про доработку под ваш шаблон
    wb.save(output_path)
    print(f"Saved: {output_path} (items: {len(items)})")


if __name__ == "__main__":
    example_lot = {
        "manager": "Батыр",
        "supplier": "RG GOLD",
        "lot_number": "T-0003701",
        "calc_date": date.today().strftime("%d.%m.%Y"),
        "lot_start": "19.06.2026",
        "lot_end": "25.06.2026",
        "lead_time_days": 10,
        "markup_coef": 1.5,
        "usd_rate": 486.19,
        "item_name": "Песок (отсев) + доставка",
        "qty": 150,
        "purchase_price_ddp": 8500,
    }
    fill_single("template.xlsx", "output_filled.xlsx", example_lot)
