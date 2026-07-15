"""
Python-зеркало формул из template_kz-kz.xlsx и template_foreign.xlsx.

Нужно, чтобы в форме можно было увидеть итоговую прибыль ЖИВЬЁМ, по мере
заполнения полей - не открывая каждый раз сгенерированный Excel. Формулы
здесь должны быть математически идентичны формулам в самих .xlsx файлах;
если меняете один - меняйте и второй, иначе живой калькулятор в форме
разойдётся с тем, что реально посчитает Excel.
"""
from dataclasses import dataclass, field


# ============================== KZ -> KZ ==================================

def compute_kz(header: dict, items: list[dict]) -> dict:
    """header: markup_coef (J9), usd_rate (K9), road_cost (H18).
    item: qty, purchase_price_ddp, extra_cost (опц., def 0)."""
    markup = header["markup_coef"]
    usd_rate = header["usd_rate"] or 1
    road_cost = header.get("road_cost") or 0

    rows = []
    totals = dict.fromkeys(
        ["F", "G", "H", "K", "L", "M", "N", "O", "P", "Q", "R", "S", "T"], 0.0
    )
    for item in items:
        d = item["qty"]
        e = item["purchase_price_ddp"]
        t = item.get("extra_cost") or 0

        f = e * d
        g = f * 16 / 116
        h = f - g
        j = e * markup
        k = j * d
        l = k * 16 / 116
        m = l - g
        n = k - l
        o = n - h
        p = f * 0.004
        q = (o - p) * 0.20
        r = o - q - p - t
        s = r * 0.06

        rows.append(dict(name=item.get("item_name") or item.get("name"), qty=d,
                          purchase_price=e, sale_price=j, sale_sum_vat=k,
                          gross_margin=o, bank_fee=p, profit_tax=q,
                          profit=r, extra_cost=t))
        for key, val in zip(
            ["F", "G", "H", "K", "L", "M", "N", "O", "P", "Q", "R", "S", "T"],
            [f, g, h, k, l, m, n, o, p, q, r, s, t],
        ):
            totals[key] += val

    vat_payable = totals["G"] + totals["M"]  # H15 "НДС" = G13+M13
    total_costs = (totals["H"] + vat_payable + totals["Q"] + totals["S"]
                    + road_cost + totals["P"] + totals["T"])
    contract_sum = totals["K"]
    profit_kzt = contract_sum - total_costs
    profit_usd = profit_kzt / usd_rate if usd_rate else 0
    profit_pct = (profit_kzt / contract_sum * 100) if contract_sum else 0

    return dict(
        rows=rows, totals=totals, road_cost=road_cost,
        total_costs=total_costs, contract_sum=contract_sum,
        profit_kzt=profit_kzt, profit_usd=profit_usd, profit_pct=profit_pct,
    )


# ============================ Foreign -> KZ ================================

def compute_foreign(header: dict, items: list[dict]) -> dict:
    """header: markup_coef (L9), vat_rate (O9, def 0.16), road_cost (H9, В
    ВАЛЮТЕ ЗАКУПКИ), usd_rate (AF9 - курс валюты закупки к тенге).
    item: qty, unit, price_fca (цена FCA за ед., В ВАЛЮТЕ ЗАКУПКИ - не тенге!),
    sale_price_kzt (цена продажи тнг/шт - это уже конечная цена для клиента
    в Казахстане, тенге), duty_rate, truck_count, overhead (В ВАЛЮТЕ ЗАКУПКИ,
    опц., def 500), extra_cost (В ВАЛЮТЕ ЗАКУПКИ, опц., def 0).

    Вся цепочка себестоимости (FCA -> Дорога -> DAP -> Вход DAP -> пошлина/
    НДС/сборы/накладные/доп.расходы -> DDP) считается в валюте закупки -
    ровно как в самом .xlsx. В тенге переводится только константа брокерского
    сбора (25950 тнг/декларация) и итоговая цена продажи клиенту."""
    markup = header["markup_coef"]
    vat_rate = header.get("vat_rate", 0.16)
    road_total = header.get("road_cost") or 0  # в валюте закупки
    rate = header["usd_rate"] or 1

    prelim = []
    g_total = 0.0
    for item in items:
        e = item["qty"]
        f = item["price_fca"]
        g = f * e
        g_total += g
        prelim.append((item, e, f, g))

    rows = []
    totals = dict.fromkeys(
        ["G", "I", "K", "M", "N", "O", "P", "Q", "S", "U", "V", "W", "Y",
         "AB", "AC", "AD", "AF", "AI"], 0.0
    )
    for item, e, f, g in prelim:
        h = (g / g_total * road_total / e) if g_total and e else 0  # Дорога, цена/ед
        i = h * e
        j = f + h              # DAP цена/ед
        k = j * e
        l = j * markup          # Вход DAP цена/ед
        m = l * e
        duty_rate = item["duty_rate"]
        n = m * duty_rate       # Имп. пошлина
        o = (m + n) * vat_rate  # НДС вход
        truck_count = item["truck_count"]
        q = (25950 / rate) * truck_count  # Сборы (тенге -> валюта закупки)
        overhead = item.get("overhead") or 0
        p = overhead
        extra_cost = item.get("extra_cost") or 0
        r = (m + n + o + q + p + extra_cost) / e  # DDP цена/шт (валюта закупки)
        s = r * e                                   # DDP сумма (валюта закупки)

        aa = item["sale_price_kzt"]
        t = aa / rate
        u = t * e
        v = u * 0.16
        w = v - o
        x = t * 1.16
        y = x * e

        ab = aa * e
        ac = ab * 0.16
        ad = ac - o * rate
        ae = aa * 1.16
        af = ae * e

        rows.append(dict(
            name=item.get("name"), qty=e, road_price=h, dap_price=j,
            entry_dap_price=l, duty=n, import_vat=o, broker_fees=q,
            overhead=p, ddp_price=r, sale_price_kzt=aa,
            sale_sum_kzt=ab, extra_cost=extra_cost,
        ))
        for key, val in zip(
            ["G", "I", "K", "M", "N", "O", "P", "Q", "S", "U", "V", "W", "Y",
             "AB", "AC", "AD", "AF", "AI"],
            [g, i, k, m, n, o, p, q, s, u, v, w, y, ab, ac, ad, af, extra_cost],
        ):
            totals[key] += val

    # Block 1 - "Разница" -> чистая прибыль. AI (доп.расходы) уже вошли в S
    # через R12, отдельно вычитать их здесь снова - задваивать расход.
    s16 = totals["Y"] - totals["S"] - totals["W"]
    s17 = totals["M"] * 0.007
    s18 = (s16 - s17) * 0.20
    s19 = (s16 - (s17 + s18)) * 0.06
    s20 = s16 - (s17 + s18 + s19)

    # Block 2 - отдельная $-маржа между "Вход DAP" и "DAP" (см. предупреждение
    # в чате - оставлено как в оригинальном шаблоне, не редактировалось)
    s23 = (totals["M"] - totals["K"]) / 1.15
    s24 = s23
    s26 = s20 + s24

    return dict(
        rows=rows, totals=totals, road_total=road_total,
        razmnitsa=s16, bank_fee=s17, profit_tax=s18, dividend_tax=s19,
        profit_net_block1=s20, block2_margin=s24, profit_total=s26,
        profit_pct=(s26 / totals["Y"] * 100) if totals["Y"] else 0,
    )
