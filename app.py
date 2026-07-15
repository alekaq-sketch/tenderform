"""Heat Energy - Streamlit tender calculator."""

import os
import tempfile
from datetime import date

import pandas as pd
import streamlit as st
from streamlit.errors import StreamlitSecretNotFoundError

from extract_heuristic import extract_items as extract_items_free
from extract_raw import extract_any
from extract_with_llm import extract_fields as extract_items_llm
from fetch_usd_rate import get_rate, currency_for_country
from fill_tender_template import fill_multi, fill_multi_foreign
from calc_engine import compute_kz, compute_foreign


st.set_page_config(
    page_title="Heat Energy · Tender Calculator",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# NOTE: widgets rendered as canvas/iframe components (st.data_editor,
# st.file_uploader) take their colors from the Streamlit *theme*
# (.streamlit/config.toml), not from this CSS. The theme is set to match
# these colors — see .streamlit/config.toml shipped alongside this file.
st.markdown(
    """
<style>
  @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
  @import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@500;600&display=swap');

  :root {
    --ink: #1e252d;
    --ink-soft: #5c6773;
    --paper: #faf6ec;
    --paper-2: #f2ebdb;
    --line: #ddd2ae;
    --teal: #186b5d;
    --teal-deep: #124f45;
    --ember: #c17a3f;
    --ember-soft: #e4a468;
  }

  .stApp {
    background-color: #0b1220;
    background-image:
      radial-gradient(ellipse 80% 60% at 12% 15%, rgba(24, 107, 93, 0.24) 0%, transparent 55%),
      radial-gradient(ellipse 65% 55% at 88% 80%, rgba(193, 122, 63, 0.14) 0%, transparent 52%),
      linear-gradient(160deg, #0b1220 0%, #121c2a 40%, #182132 75%, #0e1622 100%);
    background-attachment: fixed;
    font-family: "Inter", sans-serif;
  }

  header[data-testid="stHeader"] { background: transparent; }
  [data-testid="stSidebar"], [data-testid="collapsedControl"] { display: none; }

  div.block-container {
    position: relative;
    background: linear-gradient(180deg, var(--paper) 0%, var(--paper-2) 100%);
    border-radius: 14px;
    padding: 2.75rem 2.25rem 2.5rem;
    margin-top: 1.5rem;
    max-width: 920px;
    box-shadow:
      0 2px 0 rgba(255, 255, 255, 0.5) inset,
      0 32px 64px rgba(0, 0, 0, 0.45),
      0 8px 24px rgba(0, 0, 0, 0.25);
    color: var(--ink);
  }
  /* signature detail: a folded corner tab, like a stamped tender form */
  div.block-container::before {
    content: "";
    position: absolute;
    top: 0;
    left: 2.25rem;
    width: 46px;
    height: 6px;
    border-radius: 0 0 4px 4px;
    background: linear-gradient(90deg, var(--teal), var(--ember-soft));
  }

  h1, h2, h3 { color: var(--ink) !important; }

  .app-header-row {
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    gap: 1.25rem;
    margin-bottom: 0.35rem;
    padding-top: 0.5rem;
  }
  .app-header-main h1 {
    font-size: 1.55rem !important;
    font-weight: 700 !important;
    margin: 0 0 0.2rem !important;
    line-height: 1.2 !important;
    letter-spacing: -0.01em;
  }
  .app-header-main h1 .dot {
    color: var(--ember);
  }
  .app-header-sub {
    color: var(--ink-soft);
    font-size: 0.92rem;
    margin: 0;
  }
  .hdr-badges {
    display: flex;
    gap: 0.6rem;
    justify-content: flex-end;
    flex-wrap: nowrap;
    flex-shrink: 0;
    padding-top: 0.15rem;
  }
  .hdr-badge {
    background: rgba(255, 255, 255, 0.9);
    border: 1px solid var(--line);
    border-left: 3px solid var(--teal);
    border-radius: 8px;
    padding: 0.5rem 0.85rem;
    min-width: 7.5rem;
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
  }
  .hdr-badge-label {
    display: block;
    font-size: 0.66rem;
    font-weight: 600;
    letter-spacing: 0.09em;
    text-transform: uppercase;
    color: var(--teal);
    margin-bottom: 0.2rem;
  }
  .hdr-badge-value {
    display: block;
    font-family: "IBM Plex Mono", monospace;
    font-size: 0.92rem;
    font-weight: 600;
    color: var(--ink);
    white-space: nowrap;
  }

  hr, div[data-testid="stDivider"] { border-color: var(--line) !important; }

  .step-title {
    display: flex;
    align-items: center;
    gap: 0.6rem;
    font-size: 1.02rem;
    font-weight: 600;
    color: var(--ink);
    margin: 0 0 0.85rem;
  }
  .step-title span.num {
    font-family: "IBM Plex Mono", monospace;
    font-size: 0.78rem;
    font-weight: 600;
    color: var(--paper);
    background: var(--teal);
    border-radius: 5px;
    padding: 0.18rem 0.45rem;
  }

  .section-card {
    background: rgba(255, 255, 255, 0.82);
    border: 1px solid var(--line);
    border-radius: 10px;
    padding: 1.15rem 1.3rem;
    margin-bottom: 0.75rem;
    box-shadow: 0 2px 12px rgba(0, 0, 0, 0.04);
  }

  div[data-testid="stTextInput"] label,
  div[data-testid="stNumberInput"] label {
    font-size: 0.84rem !important;
    font-weight: 500 !important;
    color: var(--ink-soft) !important;
  }
  div[data-testid="stTextInput"] input,
  div[data-testid="stNumberInput"] input,
  div[data-testid="stTextArea"] textarea {
    border-radius: 7px;
    border-color: var(--line);
    background: #fff;
    color: var(--ink);
    font-family: "IBM Plex Mono", monospace;
    font-size: 0.9rem;
  }
  div[data-testid="stTextInput"] input:focus,
  div[data-testid="stNumberInput"] input:focus,
  div[data-testid="stTextArea"] textarea:focus {
    border-color: var(--ember) !important;
    box-shadow: 0 0 0 1px var(--ember) !important;
  }

  div[data-testid="stFileUploader"] label { display: none; }
  [data-testid="stFileUploaderDropzone"] {
    border-radius: 10px !important;
  }

  .stButton > button,
  div[data-testid="stDownloadButton"] > button {
    border-radius: 7px !important;
    font-weight: 600 !important;
    font-size: 0.88rem !important;
    border: 1px solid var(--line) !important;
    background: #fff !important;
    color: var(--ink) !important;
    box-shadow: none !important;
    outline: none !important;
    transition: background .15s ease, border-color .15s ease, color .15s ease;
  }
  .stButton > button:hover,
  div[data-testid="stDownloadButton"] > button:hover {
    border-color: var(--ember) !important;
    color: var(--teal-deep) !important;
    background: #fff8f0 !important;
  }
  .stButton > button:focus-visible,
  div[data-testid="stDownloadButton"] > button:focus-visible {
    outline: none !important;
    box-shadow: 0 0 0 2px var(--ember-soft) !important;
  }
  .stButton > button[kind="primary"],
  div[data-testid="stDownloadButton"] > button[kind="primary"] {
    background: linear-gradient(135deg, var(--teal), var(--teal-deep)) !important;
    color: #fff !important;
    border: none !important;
    box-shadow: 0 4px 14px rgba(24, 107, 93, 0.35) !important;
  }
  .stButton > button[kind="primary"]:hover,
  div[data-testid="stDownloadButton"] > button[kind="primary"]:hover {
    color: #fff !important;
    box-shadow: 0 4px 16px rgba(193, 122, 63, 0.45) !important;
  }
  .stButton > button:disabled {
    opacity: 0.65 !important;
    background: #ece7da !important;
    color: var(--ink-soft) !important;
    border: 1px dashed var(--line) !important;
  }

  [data-testid="stToast"] { font-family: "Inter", sans-serif; }
  /* lot-type radio, rendered as pill-style segmented control */
  div[role="radiogroup"] {
    gap: 0.5rem;
  }
  div[role="radiogroup"] label {
    background: #fff;
    border: 1px solid var(--line);
    border-radius: 7px;
    padding: 0.35rem 0.9rem !important;
  }
  div[role="radiogroup"] label:has(input:checked) {
    border-color: var(--teal);
    background: #eef6f3;
  }

  /* live-calculator metric cards */
  div[data-testid="stMetric"] {
    background: #fff;
    border: 1px solid var(--line);
    border-radius: 8px;
    padding: 0.6rem 0.8rem;
  }
  div[data-testid="stMetricLabel"] { color: var(--ink-soft) !important; }
  div[data-testid="stMetricValue"] {
    font-family: "IBM Plex Mono", monospace;
    color: var(--teal-deep) !important;
  }

</style>
""",
    unsafe_allow_html=True,
)
TEMPLATE_PATHS = {"kz": "template_kz-kz.xlsx", "foreign": "template_foreign.xlsx"}
CURRENCY_LABELS = {"USD": "USD", "RUB": "RUB", "EUR": "EUR"}


def init_state() -> None:
    st.session_state.setdefault("lot_type", "kz")
    st.session_state.setdefault("items_kz", [])
    st.session_state.setdefault("items_foreign", [])
    st.session_state.setdefault(
        "header",
        {
            "manager": "", "supplier": "", "lot_number": "",
            "calc_date": date.today().strftime("%d.%m.%Y"),
            "lot_start": "", "lot_end": "",
            "lead_time_days": 10, "delivery_days": 30,
            "markup_coef_kz": 1.5, "markup_coef_fx": 1.2,
            "usd_rate": 0.0, "fx_rate": 0.0,
            "road_cost_kz": 0.0, "road_cost_fx": 0.0,
            "vat_rate": 0.16,
            "currency": "USD",
        },
    )
    st.session_state.setdefault("raw_text", "")
    st.session_state.setdefault("generated_file", None)
    st.session_state.setdefault("generated_name", "расчёт.xlsx")

    h = st.session_state["header"]
    defaults = {
        "fld_manager": h["manager"], "fld_supplier": h["supplier"],
        "fld_lot_number": h["lot_number"], "fld_calc_date": h["calc_date"],
        "fld_lot_start": h["lot_start"], "fld_lot_end": h["lot_end"],
        "fld_lead_time_days": int(h["lead_time_days"]),
        "fld_delivery_days": int(h["delivery_days"]),
        "fld_markup_coef_kz": float(h["markup_coef_kz"]),
        "fld_markup_coef_fx": float(h["markup_coef_fx"]),
        "fld_usd_rate": float(h["usd_rate"]),
        "fld_fx_rate": float(h["fx_rate"]),
        "fld_road_cost_kz": float(h["road_cost_kz"]),
        "fld_road_cost_fx": float(h["road_cost_fx"]),
        "fld_vat_rate": float(h["vat_rate"]) * 100,
        "fld_currency": h["currency"],
    }
    for key, value in defaults.items():
        st.session_state.setdefault(key, value)


def format_date_input(value: str) -> str:
    digits = "".join(c for c in value if c.isdigit())[:8]
    if len(digits) <= 2:
        return digits
    if len(digits) <= 4:
        return f"{digits[:2]}.{digits[2:]}"
    return f"{digits[:2]}.{digits[2:4]}.{digits[4:]}"


def validate_date(value: str, *, required: bool = False) -> tuple[str, str | None]:
    formatted = format_date_input(value)
    if not formatted:
        return formatted, "Укажите дату" if required else None

    parts = formatted.split(".")
    if len(parts) == 1:
        return formatted, None
    if len(parts) == 2:
        day_s, month_s = parts
        if day_s and (not day_s.isdigit() or int(day_s) < 1 or int(day_s) > 31):
            return formatted, "День должен быть от 01 до 31"
        if month_s and (not month_s.isdigit() or int(month_s) < 1 or int(month_s) > 12):
            return formatted, "Месяц должен быть от 01 до 12"
        return formatted, None

    day_s, month_s, year_s = parts[0], parts[1], parts[2]
    if not (day_s.isdigit() and month_s.isdigit() and year_s.isdigit()):
        return formatted, "Дата должна быть в формате дд.мм.гггг"
    day, month, year = int(day_s), int(month_s), int(year_s)
    if day < 1 or day > 31:
        return formatted, "День должен быть от 01 до 31"
    if month < 1 or month > 12:
        return formatted, "Месяц должен быть от 01 до 12"
    if len(year_s) < 4:
        return formatted, None
    if year < 2000 or year > 2100:
        return formatted, "Год должен быть от 2000 до 2100"
    return formatted, None


@st.cache_data(ttl=3600, show_spinner=False)
def fetch_rate_cached(currency: str) -> float:
    """Raises on failure so the caller can show the real error."""
    return get_rate(currency)


def normalize_item_kz(item: dict) -> dict:
    return {
        "name": str(item.get("name") or "").strip(),
        "qty": max(0, int(item.get("qty") or 0)),
        "purchase_price_ddp": max(0.0, float(item.get("purchase_price_ddp") or 0)),
        "extra_cost": max(0.0, float(item.get("extra_cost") or 0)),
    }


def normalize_item_fx(item: dict) -> dict:
    return {
        "name": str(item.get("name") or "").strip(),
        "unit": str(item.get("unit") or "").strip(),
        "qty": max(0, int(item.get("qty") or 0)),
        "price_fca": max(0.0, float(item.get("price_fca") or 0)),
        "sale_price_kzt": max(0.0, float(item.get("sale_price_kzt") or 0)),
        "duty_rate_pct": max(0.0, float(item.get("duty_rate_pct") or 0)),
        "truck_count": max(1, int(item.get("truck_count") or 1)),
        "overhead": max(0.0, float(item.get("overhead") if item.get("overhead") is not None else 500)),
        "extra_cost": max(0.0, float(item.get("extra_cost") or 0)),
        "country": str(item.get("country") or "").strip(),
        "tnved": str(item.get("tnved") or "").strip(),
        "transport": str(item.get("transport") or "").strip(),
    }


def get_secret(name: str, default: str = "") -> str:
    try:
        return st.secrets.get(name, default)
    except StreamlitSecretNotFoundError:
        return default


def save_uploaded_file(uploaded_file) -> str:
    suffix = os.path.splitext(uploaded_file.name)[1]
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(uploaded_file.getbuffer())
        return tmp.name


def has_valid_items(items: list[dict]) -> bool:
    return bool(items) and any(item.get("name") for item in items)


def on_calc_date_change() -> None:
    st.session_state.fld_calc_date = format_date_input(st.session_state.fld_calc_date)


def on_lot_start_change() -> None:
    st.session_state.fld_lot_start = format_date_input(st.session_state.fld_lot_start)


def on_lot_end_change() -> None:
    st.session_state.fld_lot_end = format_date_input(st.session_state.fld_lot_end)


def show_date_error(message: str | None) -> None:
    if message:
        st.markdown(
            f'<p style="color:#b94e2b;font-size:0.85rem;margin:0.15rem 0 0.5rem;">{message}</p>',
            unsafe_allow_html=True,
        )


def step_heading(number: str, title: str) -> None:
    st.markdown(
        f'<p class="step-title"><span class="num">{number}</span>{title}</p>',
        unsafe_allow_html=True,
    )


def fmt_money(value: float, suffix: str = " тнг") -> str:
    try:
        return f"{value:,.0f}{suffix}".replace(",", " ")
    except (TypeError, ValueError):
        return f"0{suffix}"


init_state()
is_foreign = st.session_state.get("fld_lot_type_radio", "Казахстан → Казахстан") != "Казахстан → Казахстан"

# ------------------------------------------------- Плавающий калькулятор ---
# Обычный арифметический калькулятор "для прикидок", не связанный с бизнес-
# логикой формы. Живёт в собственном iframe и держит своё состояние в JS
# (window.frameElement), поэтому не сбрасывается при каждом st.rerun формы -
# перепрошивка позиции происходит один раз при загрузке фрейма, а сам фрейм
# Streamlit не перемонтирует, пока его HTML не меняется между прогонами.
st.iframe(
    """
<style>
  #calc-shell { position: fixed; top: 110px; right: 22px; z-index: 999999;
    font-family: Inter, sans-serif; }
  #calc-box { width: 220px; background: linear-gradient(180deg,#faf6ec,#f2ebdb);
    border: 1px solid #ddd2ae; border-radius: 10px;
    box-shadow: 0 12px 28px rgba(0,0,0,0.35); overflow: hidden; }
  #calc-head { display:flex; justify-content:space-between; align-items:center;
    background:#186b5d; color:#fff; font-size:12.5px; font-weight:600;
    padding:6px 10px; cursor:pointer; user-select:none; }
  #calc-toggle { opacity:0.85; }
  #calc-screen { font-family:"IBM Plex Mono",monospace; text-align:right;
    font-size:20px; padding:10px 12px; color:#1e252d; background:#fff;
    border-bottom:1px solid #ddd2ae; overflow:hidden; text-overflow:ellipsis; }
  #calc-grid { display:grid; grid-template-columns:repeat(4,1fr); gap:1px;
    background:#ddd2ae; }
  #calc-grid button { border:none; background:#fff; padding:11px 0;
    font-size:14.5px; color:#1e252d; cursor:pointer; font-family:Inter,sans-serif; }
  #calc-grid button:hover { background:#fdf3e7; }
  #calc-grid button.op { background:#f2ebdb; color:#186b5d; font-weight:600; }
  #calc-grid button.eq { background:#c17a3f; color:#fff; font-weight:700; }
  #calc-grid button.eq:hover { background:#a8672f; }
  #calc-body.collapsed { display:none; }
</style>
<div id="calc-shell">
  <div id="calc-box">
    <div id="calc-head" onclick="var b=document.getElementById('calc-body'); var t=document.getElementById('calc-toggle'); b.classList.toggle('collapsed'); t.textContent = b.classList.contains('collapsed') ? '▸' : '▾';">
      <span>Калькулятор</span><span id="calc-toggle">▾</span>
    </div>
    <div id="calc-body">
      <div id="calc-screen">0</div>
      <div id="calc-grid"></div>
    </div>
  </div>
</div>
<script>
(function () {
  var screen = document.getElementById('calc-screen');
  var grid = document.getElementById('calc-grid');
  var keys = ['C','⌫','%','÷', '7','8','9','×', '4','5','6','-', '1','2','3','+', '0','00','.','='];
  var expr = '';

  function render() { screen.textContent = expr === '' ? '0' : expr; }

  function press(k) {
    if (k === 'C') { expr = ''; }
    else if (k === '⌫') { expr = expr.slice(0, -1); }
    else if (k === '=') {
      try {
        var safe = expr.replace(/×/g, '*').replace(/÷/g, '/').replace(/%/g, '/100');
        if (!/^[0-9+\\-*/.() ]*$/.test(safe)) throw new Error('bad');
        var result = Function('"use strict"; return (' + safe + ')')();
        expr = String(Math.round(result * 1e8) / 1e8);
      } catch (e) { expr = 'Ошибка'; }
    } else { expr = (expr === 'Ошибка' ? '' : expr) + k; }
    render();
  }

  keys.forEach(function (k) {
    var btn = document.createElement('button');
    btn.textContent = k;
    if (['÷','×','-','+','%'].includes(k)) btn.className = 'op';
    if (k === '=') btn.className = 'eq';
    btn.onclick = function () { press(k); };
    grid.appendChild(btn);
  });

  // Escape the iframe box so the calculator floats over the whole page,
  // pinned to the right, regardless of where this component sits in the
  // Streamlit layout. Same-origin iframe, so parent DOM access is allowed.
  try {
    var fe = window.frameElement;
    if (fe) {
      fe.style.position = 'fixed';
      fe.style.top = '0';
      fe.style.right = '0';
      fe.style.width = '260px';
      fe.style.height = '100vh';
      fe.style.border = 'none';
      fe.style.zIndex = 999999;
      fe.style.pointerEvents = 'auto';
      document.getElementById('calc-shell').style.pointerEvents = 'auto';
    }
  } catch (e) {}
})();
</script>
""",
    height=1,
)

# ---------------------------------------------------------------- Header ---
lot_display = st.session_state.fld_lot_number.strip() or "не указан"
date_display = st.session_state.fld_calc_date.strip() or date.today().strftime("%d.%m.%Y")
st.markdown(
    f"""
<div class="app-header-row">
  <div class="app-header-main">
    <h1>Heat Energy<span class="dot">.</span> Tender Calculator</h1>
    <p class="app-header-sub">Калькулятор тендерных расчётов и подготовки Excel</p>
  </div>
  <div class="hdr-badges">
    <div class="hdr-badge">
      <span class="hdr-badge-label">Лот</span>
      <span class="hdr-badge-value">{lot_display}</span>
    </div>
    <div class="hdr-badge">
      <span class="hdr-badge-label">Дата</span>
      <span class="hdr-badge-value">{date_display}</span>
    </div>
  </div>
</div>
""",
    unsafe_allow_html=True,
)

st.divider()

# ------------------------------------------------------- Step 0: тип лота --
step_heading("01", "Тип лота")
lot_type_choice = st.radio(
    "Тип лота", ["Казахстан → Казахстан", "Закупка за рубежом → Казахстан"],
    key="fld_lot_type_radio", horizontal=True, label_visibility="collapsed",
)
lot_type = "foreign" if lot_type_choice != "Казахстан → Казахстан" else "kz"
st.session_state["lot_type"] = lot_type

# ------------------------------------------------- Step 1: загрузка файла --
st.divider()
step_heading("02", "Загрузите документ")
st.markdown('<div class="section-card">', unsafe_allow_html=True)

uploaded_file = st.file_uploader(
    "ТЗ или спецификация (.docx, .xlsx, .pdf)",
    type=["docx", "xlsx", "pdf"],
    accept_multiple_files=False,
)
st.caption("Распознавание достаёт наименование/ед.изм/кол-во/цену из документа. "
           "Валюта, пошлина, кол-во машин, цена продажи, доп.расходы — это ваши "
           "бизнес-решения, документ их не содержит, заполните их вручную на шаге ниже.")

recognize_btn = st.button("Распознать", type="primary", disabled=uploaded_file is None)

if uploaded_file and recognize_btn:
    tmp_path = save_uploaded_file(uploaded_file)
    try:
        with st.spinner("Читаю документ..."):
            raw_text = extract_any(tmp_path)
            extracted_items = extract_items_free(tmp_path)
        st.session_state["raw_text"] = raw_text[:8000]
        if lot_type == "kz":
            st.session_state["items_kz"] = [
                normalize_item_kz({"name": it.get("name"), "qty": it.get("qty"),
                                    "purchase_price_ddp": it.get("unit_price")})
                for it in extracted_items
            ]
            st.session_state.pop("items_kz_editor", None)
        else:
            st.session_state["items_foreign"] = [
                normalize_item_fx({"name": it.get("name"), "unit": it.get("unit"),
                                    "qty": it.get("qty"), "price_fca": it.get("unit_price"),
                                    "duty_rate_pct": 5.0})
                for it in extracted_items
            ]
            st.session_state.pop("items_foreign_editor", None)
        st.session_state["generated_file"] = None
        st.success(f"Найдено позиций: {len(extracted_items)}")
    except Exception as exc:
        st.error(f"Ошибка распознавания: {exc}")
    finally:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)

if st.session_state["raw_text"]:
    with st.expander("Сырой текст документа", expanded=False):
        st.text_area(
            "raw_preview", st.session_state["raw_text"], height=180,
            label_visibility="collapsed", disabled=True,
        )

st.markdown("</div>", unsafe_allow_html=True)

st.markdown('<div class="section-card">', unsafe_allow_html=True)
st.markdown("**Распознавание через LLM** *(опционально)*")

api_key = st.text_input(
    "Anthropic API ключ", value=get_secret("ANTHROPIC_API_KEY"),
    type="password", placeholder="Введите API-ключ...",
)

if st.button("Распознать через LLM", disabled=not api_key):
    if not st.session_state["raw_text"]:
        st.warning("Сначала загрузите документ и нажмите «Распознать».")
    else:
        try:
            with st.spinner("Claude анализирует документ..."):
                result = extract_items_llm(st.session_state["raw_text"], api_key=api_key)
            extracted_items = result.get("items", [])
            if lot_type == "kz":
                st.session_state["items_kz"] = [
                    normalize_item_kz({"name": it.get("name"), "qty": it.get("qty"),
                                        "purchase_price_ddp": it.get("unit_price")})
                    for it in extracted_items
                ]
                st.session_state.pop("items_kz_editor", None)
            else:
                st.session_state["items_foreign"] = [
                    normalize_item_fx({"name": it.get("name"), "unit": it.get("unit"),
                                        "qty": it.get("qty"), "price_fca": it.get("unit_price"),
                                        "duty_rate_pct": 5.0})
                    for it in extracted_items
                ]
                st.session_state.pop("items_foreign_editor", None)
            st.session_state["generated_file"] = None
            st.success(f"LLM нашёл позиций: {len(extracted_items)}")
        except Exception as exc:
            st.error(f"Ошибка LLM: {exc}")

st.markdown("</div>", unsafe_allow_html=True)

# ------------------------------------------------------- Step 2: товары ----
st.divider()
step_heading("03", "Проверьте позиции")
st.caption("Чтобы удалить строку: выделите её слева (наведите на номер строки) "
           "и нажмите на значок корзины сверху таблицы, либо клавишу Delete — "
           "строка исчезнет сразу, без лишних шагов."
           + (" Страна происхождения / ТН ВЭД / транспорт указываются на каждый "
              "товар отдельно — они могут отличаться от позиции к позиции."
              if lot_type == "foreign" else ""))

if lot_type == "kz":
    current_items = st.session_state["items_kz"] or [
        {"name": "", "qty": 0, "purchase_price_ddp": 0.0, "extra_cost": 0.0}
    ]
    items_df = pd.DataFrame(current_items, columns=["name", "qty", "purchase_price_ddp",
                                                      "extra_cost"])
    edited_df = st.data_editor(
        items_df, width="stretch", hide_index=True, num_rows="dynamic",
        column_config={
            "name": st.column_config.TextColumn("Наименование", width="large"),
            "qty": st.column_config.NumberColumn("Кол-во", min_value=0, step=1, format="%d"),
            "purchase_price_ddp": st.column_config.NumberColumn(
                "Цена закупки DDP (с НДС), тнг", min_value=0, step=100, format="%.2f"),
            "extra_cost": st.column_config.NumberColumn(
                "Доп.расходы (прочее), тнг", min_value=0, step=1000, format="%.2f"),
        },
        key="items_kz_editor",
    )
    # Keep every edited row (even ones without a name yet) in session_state so
    # a still-blank name doesn't wipe out qty/price the user already typed
    # into that row on the next rerun - only filter for actual use below.
    st.session_state["items_kz"] = [
        normalize_item_kz(row) for row in edited_df.fillna("").to_dict("records")
    ]
    items = [it for it in st.session_state["items_kz"] if it["name"].strip()]
else:
    current_items = st.session_state["items_foreign"] or [
        {"name": "", "unit": "", "qty": 0, "price_fca": 0.0, "sale_price_kzt": 0.0,
         "duty_rate_pct": 5.0, "truck_count": 1, "overhead": 500.0, "extra_cost": 0.0,
         "country": "", "tnved": "", "transport": ""}
    ]
    cols = ["name", "unit", "qty", "price_fca", "sale_price_kzt", "duty_rate_pct",
            "truck_count", "overhead", "extra_cost", "country", "tnved", "transport"]
    items_df = pd.DataFrame(current_items, columns=cols)
    currency_now = st.session_state.get("fld_currency", "USD")
    edited_df = st.data_editor(
        items_df, width="stretch", hide_index=True, num_rows="dynamic",
        column_config={
            "name": st.column_config.TextColumn("Наименование", width="large"),
            "unit": st.column_config.TextColumn("Ед.изм", width="small"),
            "qty": st.column_config.NumberColumn("Кол-во", min_value=0, step=1, format="%d"),
            "price_fca": st.column_config.NumberColumn(
                f"Цена FCA, {currency_now}/ед.", min_value=0, step=10, format="%.2f"),
            "sale_price_kzt": st.column_config.NumberColumn(
                "Цена продажи без НДС, тнг/шт", min_value=0, step=1000, format="%.2f"),
            "duty_rate_pct": st.column_config.NumberColumn(
                "Пошлина, %", min_value=0, max_value=100, step=0.5, format="%.1f"),
            "truck_count": st.column_config.NumberColumn(
                "Кол-во машин (=ГТД)", min_value=1, step=1, format="%d"),
            "overhead": st.column_config.NumberColumn(
                f"Накладные, {currency_now}", min_value=0, step=10, format="%.2f"),
            "extra_cost": st.column_config.NumberColumn(
                f"Доп.расходы (прочее), {currency_now}", min_value=0, step=10, format="%.2f"),
            "country": st.column_config.TextColumn("Страна происхождения", width="small"),
            "tnved": st.column_config.TextColumn("ТН ВЭД", width="small"),
            "transport": st.column_config.TextColumn(
                "Кол-во подвижных / транспорт", width="medium"),
        },
        key="items_foreign_editor",
    )
    st.session_state["items_foreign"] = [
        normalize_item_fx(row) for row in edited_df.fillna("").to_dict("records")
    ]
    items = [it for it in st.session_state["items_foreign"] if it["name"].strip()]

# --------------------------------------------------- Step 3: данные лота ---
st.divider()
step_heading("04", "Данные лота")

left_col, right_col = st.columns(2)

with left_col:
    st.text_input("Менеджер", key="fld_manager", placeholder="Введите имя...")
    st.text_input("Номер лота", key="fld_lot_number", placeholder="Введите номер лота...")
    st.text_input("Дата расчёта", key="fld_calc_date", placeholder="дд.мм.гггг",
                   on_change=on_calc_date_change)
    if st.session_state.fld_calc_date:
        show_date_error(validate_date(st.session_state.fld_calc_date, required=True)[1])

    if lot_type == "kz":
        st.number_input("Сумма дорожных расходов, тнг", key="fld_road_cost_kz",
                         min_value=0.0, step=1000.0, format="%.2f")
    else:
        st.number_input(f"Дорога, всего по лоту, {st.session_state.fld_currency}", key="fld_road_cost_fx",
                         min_value=0.0, step=1000.0, format="%.2f")

with right_col:
    st.text_input("Поставщик", key="fld_supplier", placeholder="Введите поставщика...")
    if lot_type == "kz":
        st.number_input("Коэффициент наценки", key="fld_markup_coef_kz",
                         min_value=0.01, step=0.05, format="%.2f")
    else:
        st.number_input("Коэфф. наценки (DAP → Вход DAP)", key="fld_markup_coef_fx",
                         min_value=0.01, step=0.05, format="%.2f")
        st.number_input("НДС на ввоз, %", key="fld_vat_rate",
                         min_value=0.0, max_value=100.0, step=0.5, format="%.1f")

    st.text_input("Начало лота", key="fld_lot_start", placeholder="дд.мм.гггг",
                   on_change=on_lot_start_change)
    if st.session_state.fld_lot_start:
        show_date_error(validate_date(st.session_state.fld_lot_start)[1])

    st.text_input("Окончание лота", key="fld_lot_end", placeholder="дд.мм.гггг",
                   on_change=on_lot_end_change)
    if st.session_state.fld_lot_end:
        show_date_error(validate_date(st.session_state.fld_lot_end)[1])

    st.number_input("Срок производства, дней", key="fld_lead_time_days",
                     min_value=1, step=1, format="%d")
    if lot_type == "foreign":
        st.number_input("Срок поставки, дней", key="fld_delivery_days",
                         min_value=1, step=1, format="%d")

# --- Курс валюты ---
def on_fetch_rate(currency: str, target_key: str) -> None:
    """Runs BEFORE the script reruns/re-instantiates widgets, so it's safe
    to write to st.session_state[target_key] here (unlike doing it after
    the number_input widget has already been created in the same run)."""
    try:
        rate = fetch_rate_cached(currency)
        st.session_state[target_key] = float(rate)
        st.session_state["_rate_status"] = ("success", currency, float(rate))
    except Exception as exc:
        st.session_state["_rate_status"] = ("error", currency, str(exc))


if lot_type == "kz":
    rate_left, rate_right = st.columns([3.2, 1])
    with rate_left:
        st.number_input("Курс USD, тнг (для отчёта прибыли в $)", key="fld_usd_rate",
                         min_value=0.0, step=0.01, format="%.2f")
    with rate_right:
        st.markdown("<div style='height:1.75rem'></div>", unsafe_allow_html=True)
        st.button("с Нацбанка РК", width="stretch", key="btn_rate_kz",
                   on_click=on_fetch_rate, args=("USD", "fld_usd_rate"))
else:
    cur_left, rate_left, rate_right = st.columns([1.1, 2.1, 1])
    with cur_left:
        st.selectbox("Валюта закупки", ["USD", "RUB", "EUR"], key="fld_currency")
    with rate_left:
        st.number_input(f"Курс {st.session_state.fld_currency}, тнг",
                         key="fld_fx_rate", min_value=0.0, step=0.01, format="%.2f")
    with rate_right:
        st.markdown("<div style='height:1.75rem'></div>", unsafe_allow_html=True)
        st.button("с Нацбанка РК", width="stretch", key="btn_rate_fx",
                   on_click=on_fetch_rate, args=(st.session_state.fld_currency, "fld_fx_rate"))
    countries_used = {it["country"].strip() for it in items if it.get("country")}
    suggested_currencies = {currency_for_country(c) for c in countries_used}
    if suggested_currencies and suggested_currencies != {st.session_state.fld_currency}:
        hint = ", ".join(sorted(suggested_currencies))
        st.caption(f"По странам происхождения в позициях обычно используют: {hint} — "
                   f"при необходимости переключите валюту выше.")

_rate_status = st.session_state.pop("_rate_status", None)
if _rate_status:
    _kind, _cur, _payload = _rate_status
    if _kind == "success":
        st.toast(f"Курс {_cur}: {_payload:.2f} тнг.")
    else:
        st.error(f"Не удалось получить курс {_cur}: {_payload}")

# ------------------------------------------------------------ Generate -----
st.divider()

if st.button("Сформировать расчёт", type="primary", width="stretch"):
    date_errors = [
        validate_date(st.session_state.fld_calc_date, required=True)[1],
        validate_date(st.session_state.fld_lot_start)[1] if st.session_state.fld_lot_start else None,
        validate_date(st.session_state.fld_lot_end)[1] if st.session_state.fld_lot_end else None,
    ]
    date_errors = [e for e in date_errors if e]
    template_path = TEMPLATE_PATHS[lot_type]

    if date_errors:
        st.error(date_errors[0])
    elif not has_valid_items(items):
        st.error("Добавьте хотя бы одну позицию с наименованием.")
    elif not os.path.exists(template_path):
        st.error(f"Шаблон {template_path} не найден.")
    else:
        try:
            with st.spinner("Формирую Excel..."):
                out_path = tempfile.mktemp(suffix=".xlsx")
                if lot_type == "kz":
                    if st.session_state.fld_usd_rate <= 0:
                        raise ValueError("Укажите курс USD (тг.)")
                    header = {
                        "manager": st.session_state.fld_manager.strip(),
                        "supplier": st.session_state.fld_supplier.strip(),
                        "lot_number": st.session_state.fld_lot_number.strip(),
                        "calc_date": format_date_input(st.session_state.fld_calc_date),
                        "lot_start": format_date_input(st.session_state.fld_lot_start),
                        "lot_end": format_date_input(st.session_state.fld_lot_end),
                        "lead_time_days": int(st.session_state.fld_lead_time_days),
                        "markup_coef": float(st.session_state.fld_markup_coef_kz),
                        "usd_rate": float(st.session_state.fld_usd_rate),
                        "road_cost": float(st.session_state.fld_road_cost_kz),
                    }
                    fill_multi(template_path, out_path, header, items)
                else:
                    if st.session_state.fld_fx_rate <= 0:
                        raise ValueError(f"Укажите курс {st.session_state.fld_currency} (тг.)")
                    rate = float(st.session_state.fld_fx_rate)
                    header = {
                        "manager": st.session_state.fld_manager.strip(),
                        "supplier": st.session_state.fld_supplier.strip(),
                        "lot_number": st.session_state.fld_lot_number.strip(),
                        "calc_date": format_date_input(st.session_state.fld_calc_date),
                        "lot_start": format_date_input(st.session_state.fld_lot_start),
                        "lot_end": format_date_input(st.session_state.fld_lot_end),
                        "lead_time_days": int(st.session_state.fld_lead_time_days),
                        "delivery_days": int(st.session_state.fld_delivery_days),
                        "markup_coef": float(st.session_state.fld_markup_coef_fx),
                        "vat_rate": float(st.session_state.fld_vat_rate) / 100,
                        "road_cost": float(st.session_state.fld_road_cost_fx),
                        "currency": st.session_state.fld_currency,
                        "usd_rate": rate,
                    }
                    fill_items = [
                        {**it, "duty_rate": it["duty_rate_pct"] / 100}
                        for it in items
                    ]
                    fill_multi_foreign(template_path, out_path, header, fill_items)

                with open(out_path, "rb") as f:
                    st.session_state["generated_file"] = f.read()
                os.unlink(out_path)
            st.session_state["generated_name"] = f"расчёт_{st.session_state.fld_lot_number.strip() or 'лот'}.xlsx"
            st.success("Готово. Скачайте файл ниже.")
        except Exception as exc:
            st.error(f"Ошибка при формировании: {exc}")

if st.session_state.get("generated_file"):
    st.download_button(
        "Скачать Excel", data=st.session_state["generated_file"],
        file_name=st.session_state["generated_name"],
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        type="primary", width="stretch",
    )
