"""
Заполняет шаблоны расчёта лота, не трогая формулы (только "входные" ячейки).

Два шаблона:
  fill_multi()          - template_kz-kz.xlsx      (закупка в Казахстане -> продажа в Казахстане)
  fill_multi_foreign()  - template_foreign.xlsx     (закупка за рубежом -> продажа в Казахстане)

--------------------------------------------------------------------------------------------------
Карта входных ячеек, лист "расчет", template_kz-kz.xlsx:
    B2  - ФИО менеджера / закупщика
    B3  - Поставщик
    R2  - Номер лота
    B4  - Дата расчёта
    B5  - Дата начала лота
    B6  - Дата окончания лота
    B7  - Срок производства, дней
    J9  - Коэффициент наценки (например 1.5 = +50%)
    K9  - Курс USD
    H18 - Сумма дорожных расходов
    на каждый товар (строка 12, 13, ...):
        C - Наименование
        D - Количество
        E - Цена закупки DDP (с НДС)
        T - Доп.расходы (прочее), тнг - по умолчанию 0

--------------------------------------------------------------------------------------------------
Карта входных ячеек, лист "расчет", template_foreign.xlsx:
    B2   - ФИО менеджера / закупщика
    B3   - Поставщик
    AE2  - Номер лота
    B4   - Дата расчёта
    B5   - Дата начала лота
    B6   - Дата окончания лота
    B7   - Срок производства, дней
    B8   - Срок поставки, дней
    H9   - Дорога, всего по лоту, В ВАЛЮТЕ ЗАКУПКИ (делится между товарами пропорционально сумме)
    L9   - Коэфф. наценки (DAP -> Вход DAP)
    O9   - НДС на ввоз, % (например 0.16)
    AD8  - Валюта закупки (USD/RUB/EUR) - только для наглядности в файле
    AF9  - Курс валюты закупки к тенге на дату расчёта
    на каждый товар (строка 12, 13, ...):
        C  - Наименование
        D  - Ед. изм.
        E  - Количество
        F  - Цена закупки FCA, В ВАЛЮТЕ ЗАКУПКИ (не в тенге - см. примечание выше)
        P  - Накладные, В ВАЛЮТЕ ЗАКУПКИ (по умолчанию 500)
        AA - Цена продажи без НДС, тнг/шт (это уже цена для клиента в Казахстане)
        AG - Ставка пошлины, % (своя на каждый товар)
        AH - Кол-во машин / деклараций ГТД (своё на каждый товар: 1 машина = 1 декларация)
        AI - Доп.расходы (прочее), В ВАЛЮТЕ ЗАКУПКИ (по умолчанию 0) - входит в
             себестоимость DDP наравне с "Накладные", а не отдельной строкой в прибыли
        country/tnved/transport - своё на каждый товар (см. B19/B20/B21 ниже)

    B19 - Страна происхождения (по всем товарам, если совпадает; иначе построчная разбивка)
    B20 - ТН ВЭД (аналогично)
    B21 - Кол-во подвижных / вид транспорта (аналогично)
"""
import re
import openpyxl
from datetime import date
from copy import copy
from openpyxl.cell.cell import MergedCell
from openpyxl.formula.translate import Translator
from openpyxl.styles import Alignment
from openpyxl.utils import get_column_letter

_CELL_REF_RE = re.compile(r'(\$?)([A-Za-z]{1,3})(\$?)(\d+)')


def _shift_formula_rows(formula: str, insertion_row: int, shift: int) -> str:
    """openpyxl's ws.insert_rows() physically moves cells down but does NOT
    rewrite any formula's cell references anywhere in the workbook (this is
    a documented openpyxl limitation, unlike Excel's own 'insert row' which
    fixes every reference automatically). This reproduces that missing half:
    any reference whose row is >= insertion_row gets bumped by `shift`,
    wherever in the sheet the formula lives - including formulas that moved
    together with their row, so relationships within a shifted block stay
    internally consistent."""
    def repl(m):
        col_dollar, col, row_dollar, row_s = m.groups()
        row = int(row_s)
        if row >= insertion_row:
            row += shift
        return f"{col_dollar}{col}{row_dollar}{row}"
    return _CELL_REF_RE.sub(repl, formula)


def _shift_all_formulas_below(ws, insertion_row: int, shift: int, max_row: int, max_col: int):
    for row in ws.iter_rows(min_row=1, max_row=max_row, min_col=1, max_col=max_col):
        for cell in row:
            if isinstance(cell.value, str) and cell.value.startswith("="):
                cell.value = _shift_formula_rows(cell.value, insertion_row, shift)


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
            length = max(len(line) for line in str(cell.value).split("\n"))
            widths[cell.column_letter] = max(widths.get(cell.column_letter, 0), length)

    for col, length in widths.items():
        ws.column_dimensions[col].width = min(max(length + padding, min_width), max_width)


def compose_item_name(item: dict) -> str:
    return item.get("item_name") or item.get("name") or ""


def _compose_lot_note(items: list[dict], key: str) -> str:
    """Страна/ТНВЭД/транспорт бывают разными у разных товаров одного лота
    (как и цена). Если у всех товаров значение одинаковое (или задано только
    у одного товара в лоте) - пишем его одной строкой, как раньше. Если
    значения расходятся - пишем построчную разбивку по номеру позиции, чтобы
    не потерять данные ни одного товара."""
    values = [str(item.get(key) or "").strip() for item in items]
    if not any(values):
        return ""
    if len(set(values)) == 1:
        return values[0]
    return "; ".join(f"{i + 1}) {v or '-'}" for i, v in enumerate(values))


def _copy_row_style(ws, src_row: int, dst_row: int, min_col: int, max_col: int):
    """Copies formulas (translated for the new row) + full cell style from
    src_row to dst_row, for every column in [min_col, max_col]. Used when a
    lot has more than one item and we need extra rows that behave exactly
    like the template's first item row."""
    for col_idx in range(min_col, max_col + 1):
        col = get_column_letter(col_idx)
        src = ws[f"{col}{src_row}"]
        dst = ws[f"{col}{dst_row}"]
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


def fill_single(template_path: str, output_path: str, lot: dict):
    """lot - словарь с ключами из карты выше (см. пример в __main__). Одна позиция."""
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
    ws["T12"] = lot.get("extra_cost") or 0

    wb.save(output_path)
    print(f"Saved: {output_path}")


def fill_multi(template_path: str, output_path: str, header: dict, items: list[dict]):
    """
    template_kz-kz.xlsx, несколько позиций в одном лоте.
    header - те же поля, что в fill_single, кроме item_name/qty/purchase_price_ddp.
    items  - список {"item_name", "qty", "purchase_price_ddp", "extra_cost"(опц., def. 0)}.
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
    extra = len(items) - 1
    total_row = first_row + 1  # original "Итого" row before any shifting
    sum_cols = ["D", "F", "G", "H", "K", "L", "M", "N", "O", "P", "Q", "R", "S", "T"]

    if extra > 0:
        ws.insert_rows(first_row + 1, amount=extra)
        _shift_all_formulas_below(ws, insertion_row=first_row + 1, shift=extra,
                                   max_row=60, max_col=22)
        for r in range(first_row + 1, first_row + 1 + extra):
            _copy_row_style(ws, first_row, r, min_col=2, max_col=20)  # B..T
        total_row += extra

    for i, item in enumerate(items):
        r = first_row + i
        ws[f"B{r}"] = i + 1
        ws[f"C{r}"] = compose_item_name(item)
        ws[f"D{r}"] = item["qty"]
        ws[f"E{r}"] = item["purchase_price_ddp"]
        ws[f"T{r}"] = item.get("extra_cost") or 0

    last_item_row = first_row + len(items) - 1
    for col in sum_cols:
        ws[f"{col}{total_row}"] = f"=SUM({col}{first_row}:{col}{last_item_row})"

    wb.save(output_path)
    print(f"Saved: {output_path} (items: {len(items)})")


def fill_multi_foreign(template_path: str, output_path: str, header: dict, items: list[dict]):
    """
    template_foreign.xlsx, несколько позиций в одном лоте, закупка за рубежом.

    header:
        manager, supplier, lot_number, calc_date, lot_start, lot_end,
        lead_time_days, delivery_days, markup_coef, vat_rate, road_cost
        (В ВАЛЮТЕ ЗАКУПКИ - вся цепочка себестоимости FCA->DDP считается в
        валюте закупки, не в тенге), currency ("USD"/"RUB"/"EUR", для
        пометки в файле), usd_rate (курс currency -> KZT на дату расчёта).

    items - список словарей, каждый:
        name, unit, qty,
        price_fca              - цена FCA за единицу, В ВАЛЮТЕ ЗАКУПКИ (НЕ
                                переводите в тенге - весь блок Покупка FCA/
                                Дорога/DAP/Вход DAP/Там.оформ/DDP считается
                                в валюте закупки; в тенге пересчитывается
                                только константа брокерского сбора и итоговая
                                цена продажи клиенту),
        sale_price_kzt        - цена продажи без НДС, тнг/шт (то, за сколько
                                продаём заказчику - это уже в тенге),
        duty_rate              - ставка пошлины, доля (0.05 = 5%),
        truck_count             - кол-во машин = кол-во деклараций ГТД под этот товар,
        overhead (опц., def 500)   - накладные, В ВАЛЮТЕ ЗАКУПКИ,
        extra_cost (опц., def 0)  - доп.расходы (прочее), В ВАЛЮТЕ ЗАКУПКИ,
        country/tnved/transport (опц., def "") - страна происхождения/ТНВЭД/
                                кол-во подвижных состава, своё на каждый товар.
                                Если у всех товаров лота значение одинаковое -
                                в B19/B20/B21 попадает одна строка; если разное -
                                построчная разбивка по номеру позиции (см.
                                _compose_lot_note).
    """
    wb = openpyxl.load_workbook(template_path)
    ws = wb["расчет"]

    ws["B2"] = header["manager"]
    ws["B3"] = header["supplier"]
    ws["AE2"] = f'лот {header["lot_number"]}'
    ws["B4"] = f'Дата:{header["calc_date"]}'
    ws["B5"] = f'Дата начала лота:{header["lot_start"]}'
    ws["B6"] = f'Дата окончания лота: {header["lot_end"]}'
    ws["B7"] = f'Срок производства: {header["lead_time_days"]} дн'
    ws["B8"] = f'Срок поставки: {header.get("delivery_days", 30)} календарных дней'

    ws["L9"] = header["markup_coef"]
    ws["O9"] = header.get("vat_rate", 0.16)
    ws["H9"] = header.get("road_cost") or 0
    ws["AD8"] = header.get("currency", "USD")
    ws["AF9"] = header["usd_rate"]

    first_row = 12
    extra = len(items) - 1
    total_row = first_row + 1
    sum_cols = ["E", "G", "I", "K", "M", "N", "O", "P", "Q", "S", "U", "V", "W", "Y",
                "AB", "AC", "AD", "AF", "AI"]

    if extra > 0:
        ws.insert_rows(first_row + 1, amount=extra)
        _shift_all_formulas_below(ws, insertion_row=first_row + 1, shift=extra,
                                   max_row=90, max_col=36)
        for r in range(first_row + 1, first_row + 1 + extra):
            _copy_row_style(ws, first_row, r, min_col=2, max_col=35)  # B..AI
        total_row += extra

    for i, item in enumerate(items):
        r = first_row + i
        ws[f"B{r}"] = i + 1
        ws[f"C{r}"] = compose_item_name(item)
        ws[f"D{r}"] = item.get("unit") or ""
        ws[f"E{r}"] = item["qty"]
        ws[f"F{r}"] = item["price_fca"]
        ws[f"P{r}"] = item.get("overhead") if item.get("overhead") is not None else 500
        ws[f"AA{r}"] = item["sale_price_kzt"]
        ws[f"AG{r}"] = item["duty_rate"]
        ws[f"AH{r}"] = item["truck_count"]
        ws[f"AI{r}"] = item.get("extra_cost") or 0

    last_item_row = first_row + len(items) - 1
    for col in sum_cols:
        ws[f"{col}{total_row}"] = f"=SUM({col}{first_row}:{col}{last_item_row})"

    ws["B19"] = f"Страна происхождения:{_compose_lot_note(items, 'country')}"
    ws["B20"] = f"ТНВЭД: {_compose_lot_note(items, 'tnved')}"
    ws["B21"] = f"Кол-во подвижных / вид транспорта: {_compose_lot_note(items, 'transport')}"
    if len(items) > 1:
        for coord in ("B19", "B20", "B21"):
            ws[coord].alignment = Alignment(wrap_text=True, vertical="top")

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
    fill_single("template_kz-kz.xlsx", "output_filled.xlsx", example_lot)
