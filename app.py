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
from fetch_usd_rate import get_usd_rate
from fill_tender_template import fill_multi


st.set_page_config(
    page_title="Heat Energy · Tender Calculator",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.markdown(
    """
<style>
  @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
  .stApp {
    background-color: #0a0e17;
    background-image:
      radial-gradient(ellipse 80% 60% at 15% 20%, rgba(24, 107, 93, 0.22) 0%, transparent 55%),
      radial-gradient(ellipse 70% 50% at 85% 75%, rgba(45, 100, 128, 0.18) 0%, transparent 50%),
      radial-gradient(ellipse 50% 40% at 50% 100%, rgba(249, 210, 141, 0.08) 0%, transparent 45%),
      linear-gradient(155deg, #0a0e17 0%, #121c2a 35%, #1a2332 70%, #0f1824 100%);
    background-attachment: fixed;
    font-family: "Inter", sans-serif;
  }

  header[data-testid="stHeader"] { background: transparent; }

  div.block-container {
    background: linear-gradient(180deg, #faf6ec 0%, #f3ebdb 100%);
    border-radius: 16px;
    padding: 2.25rem 2rem 2.5rem;
    margin-top: 1.5rem;
    max-width: 920px;
    box-shadow:
      0 2px 0 rgba(255, 255, 255, 0.06) inset,
      0 32px 64px rgba(0, 0, 0, 0.45),
      0 8px 24px rgba(0, 0, 0, 0.25);
    color: #1e252d;
  }

  [data-testid="stSidebar"], [data-testid="collapsedControl"] { display: none; }

  h1 { font-size: 1.65rem !important; margin-bottom: 0.15rem !important; }
  h2, h3 { color: #1e252d !important; }

  div.block-container { padding-top: 2.75rem !important; }

  .app-header-row {
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    gap: 1.25rem;
    margin-bottom: 0.35rem;
    padding-top: 0.35rem;
  }
  .app-header-main h1 {
    font-size: 1.55rem !important;
    font-weight: 700 !important;
    margin: 0 0 0.2rem !important;
    line-height: 1.2 !important;
  }
  .app-header-sub {
    color: #58606a;
    font-size: 0.92rem;
    margin: 0;
  }
  .hdr-badges {
    display: flex;
    gap: 0.65rem;
    justify-content: flex-end;
    flex-wrap: nowrap;
    flex-shrink: 0;
    padding-top: 0.15rem;
  }
  .hdr-badge {
    background: rgba(255, 255, 255, 0.88);
    border: 1px solid #d8cea9;
    border-radius: 10px;
    padding: 0.5rem 0.85rem;
    min-width: 7.5rem;
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
  }
  .hdr-badge-label {
    display: block;
    font-size: 0.68rem;
    font-weight: 600;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    color: #186b5d;
    margin-bottom: 0.2rem;
  }
  .hdr-badge-value {
    display: block;
    font-size: 0.95rem;
    font-weight: 600;
    color: #1e252d;
    white-space: nowrap;
    overflow: visible;
  }

  .step-title {
    font-size: 1.05rem;
    font-weight: 600;
    color: #1e252d;
    margin: 0 0 0.85rem;
  }
  .step-title span {
    color: #186b5d;
    font-weight: 700;
    margin-right: 0.35rem;
  }

  .section-card {
    background: rgba(255, 255, 255, 0.78);
    border: 1px solid #d8cea9;
    border-radius: 12px;
    padding: 1.15rem 1.3rem;
    margin-bottom: 0.75rem;
    box-shadow: 0 2px 12px rgba(0, 0, 0, 0.04);
  }

  div[data-testid="stTextInput"] input,
  div[data-testid="stNumberInput"] input,
  div[data-testid="stTextArea"] textarea {
    border-radius: 8px;
    border-color: #d8cea9;
    background: #fff;
  }

  .stButton > button {
    border-radius: 8px !important;
    font-weight: 600 !important;
    border: 1px solid #c5b88e !important;
    background: #fff !important;
    color: #1e252d !important;
    box-shadow: 0 1px 3px rgba(0, 0, 0, 0.06) !important;
  }
  .stButton > button:hover {
    border-color: #186b5d !important;
    color: #186b5d !important;
    background: #f8faf9 !important;
  }
  .stButton > button[kind="primary"],
  .stButton > button[data-testid="stBaseButton-primary"] {
    background: linear-gradient(135deg, #186b5d, #2d7a6a) !important;
    color: #fff !important;
    border: none !important;
    box-shadow: 0 4px 14px rgba(24, 107, 93, 0.35) !important;
  }
  .stButton > button[kind="primary"]:hover {
    color: #fff !important;
    filter: brightness(1.05);
  }
  .stButton > button:disabled {
    opacity: 0.72 !important;
    background: #ece7da !important;
    color: #58606a !important;
    border: 1px dashed #c5b88e !important;
  }

  section[data-testid="stDataEditor"],
  div[data-testid="stDataEditor"] {
    border-radius: 10px;
    border: 1px solid #d8cea9;
    background: #fff;
  }

  div[data-testid="stFileUploader"] {
    background: #fff;
    border: 1.5px dashed #c5b88e;
    border-radius: 10px;
    padding: 0.35rem;
  }
  div[data-testid="stFileUploader"] label { display: none; }
</style>
""",
    unsafe_allow_html=True,
)


def init_state() -> None:
    st.session_state.setdefault("items", [])
    st.session_state.setdefault(
        "header",
        {
            "manager": "",
            "supplier": "",
            "lot_number": "",
            "calc_date": date.today().strftime("%d.%m.%Y"),
            "lot_start": "",
            "lot_end": "",
            "lead_time_days": 10,
            "markup_coef": 1.5,
            "usd_rate": 0.0,
            "road_cost": 0.0,
        },
    )
    st.session_state.setdefault("raw_text", "")
    st.session_state.setdefault("generated_file", None)
    st.session_state.setdefault("generated_name", "расчёт.xlsx")

    header = st.session_state["header"]
    defaults = {
        "fld_manager": header["manager"],
        "fld_supplier": header["supplier"],
        "fld_lot_number": header["lot_number"],
        "fld_calc_date": header["calc_date"],
        "fld_lot_start": header["lot_start"],
        "fld_lot_end": header["lot_end"],
        "fld_lead_time_days": int(header["lead_time_days"]),
        "fld_markup_coef": float(header["markup_coef"]),
        "fld_usd_rate": float(header["usd_rate"]),
        "fld_road_cost": float(header["road_cost"]),
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
def fetch_usd_cached() -> float | None:
    try:
        return get_usd_rate()
    except Exception:
        return None


def normalize_item(item: dict) -> dict:
    return {
        "name": str(item.get("name") or "").strip(),
        "unit": str(item.get("unit") or "").strip(),
        "qty": max(0, int(item.get("qty") or 0)),
        "unit_price": max(0.0, float(item.get("unit_price") or 0)),
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


def build_excel_from_template(template_path: str, header: dict, items: list[dict]) -> bytes:
    payload_items = [
        {
            "item_name": item["name"],
            "qty": item["qty"],
            "purchase_price_ddp": item["unit_price"],
        }
        for item in items
        if item.get("name")
    ]

    with tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx") as tmp:
        out_path = tmp.name

    try:
        fill_multi(template_path, out_path, header, payload_items)
        with open(out_path, "rb") as file:
            return file.read()
    finally:
        if os.path.exists(out_path):
            os.unlink(out_path)


def sync_header_from_form() -> dict:
    header = st.session_state["header"]
    header["manager"] = st.session_state.fld_manager.strip()
    header["supplier"] = st.session_state.fld_supplier.strip()
    header["lot_number"] = st.session_state.fld_lot_number.strip()
    header["calc_date"] = format_date_input(st.session_state.fld_calc_date)
    header["lot_start"] = format_date_input(st.session_state.fld_lot_start)
    header["lot_end"] = format_date_input(st.session_state.fld_lot_end)
    header["lead_time_days"] = int(st.session_state.fld_lead_time_days)
    header["markup_coef"] = float(st.session_state.fld_markup_coef)
    header["usd_rate"] = float(st.session_state.fld_usd_rate)
    header["road_cost"] = float(st.session_state.fld_road_cost)
    return header


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
        f'<p class="step-title"><span>{number}</span>{title}</p>',
        unsafe_allow_html=True,
    )


init_state()

# Header
lot_display = st.session_state.fld_lot_number.strip() or "не указан"
date_display = st.session_state.fld_calc_date.strip() or date.today().strftime("%d.%m.%Y")
st.markdown(
    f"""
<div class="app-header-row">
  <div class="app-header-main">
    <h1>Heat Energy — Tender Calculator</h1>
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

# Step 1
step_heading("01", "Загрузите документ")
st.markdown('<div class="section-card">', unsafe_allow_html=True)

uploaded_file = st.file_uploader(
    "ТЗ или спецификация (.docx, .xlsx, .pdf)",
    type=["docx", "xlsx", "pdf"],
    accept_multiple_files=False,
)

recognize_btn = st.button("Распознать", type="primary", disabled=uploaded_file is None)

if uploaded_file and recognize_btn:
    tmp_path = save_uploaded_file(uploaded_file)
    try:
        with st.spinner("Читаю документ..."):
            raw_text = extract_any(tmp_path)
            extracted_items = extract_items_free(tmp_path)
        st.session_state["raw_text"] = raw_text[:8000]
        st.session_state["items"] = [normalize_item(item) for item in extracted_items]
        st.session_state["generated_file"] = None
        st.session_state.pop("items_editor", None)
        st.success(f"Найдено позиций: {len(st.session_state['items'])}")
    except Exception as exc:
        st.error(f"Ошибка распознавания: {exc}")
    finally:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)

if st.session_state["raw_text"]:
    with st.expander("Сырой текст документа", expanded=False):
        st.text_area(
            "raw_preview",
            st.session_state["raw_text"],
            height=180,
            label_visibility="collapsed",
            disabled=True,
        )

st.markdown("</div>", unsafe_allow_html=True)

# LLM
st.markdown('<div class="section-card">', unsafe_allow_html=True)
st.markdown("**Распознавание через LLM** *(опционально)*")

api_key = st.text_input(
    "Anthropic API ключ",
    value=get_secret("ANTHROPIC_API_KEY"),
    type="password",
    placeholder="Введите API-ключ...",
)

if st.button("Распознать через LLM", disabled=not api_key):
    if not st.session_state["raw_text"]:
        st.warning("Сначала загрузите документ и нажмите «Распознать».")
    else:
        try:
            with st.spinner("Claude анализирует документ..."):
                result = extract_items_llm(st.session_state["raw_text"], api_key=api_key)
            st.session_state["items"] = [normalize_item(item) for item in result.get("items", [])]
            st.session_state["generated_file"] = None
            st.session_state.pop("items_editor", None)
            st.success(f"LLM нашёл позиций: {len(st.session_state['items'])}")
        except Exception as exc:
            st.error(f"Ошибка LLM: {exc}")

st.markdown("</div>", unsafe_allow_html=True)

# Step 2
st.divider()
step_heading("02", "Проверьте позиции")
st.caption("Отметьте «Удалить» или очистите наименование, чтобы убрать строку.")

current_items = st.session_state["items"] or [{"name": "", "unit": "", "qty": 0, "unit_price": 0.0}]
for item in current_items:
    item.setdefault("delete", False)

items_df = pd.DataFrame(current_items, columns=["name", "unit", "qty", "unit_price", "delete"])

edited_df = st.data_editor(
    items_df,
    width="stretch",
    hide_index=True,
    num_rows="dynamic",
    column_config={
        "name": st.column_config.TextColumn("Наименование", width="large"),
        "unit": st.column_config.TextColumn("Ед. изм.", width="small"),
        "qty": st.column_config.NumberColumn("Кол-во", min_value=0, step=1, format="%d"),
        "unit_price": st.column_config.NumberColumn(
            "Цена DDP, тг.", min_value=0, step=100, format="%.2f"
        ),
        "delete": st.column_config.CheckboxColumn("Удалить", default=False),
    },
    key="items_editor",
)

st.session_state["items"] = [
    normalize_item(row)
    for row in edited_df.fillna("").to_dict("records")
    if not row.get("delete") and str(row.get("name", "")).strip()
]
items = st.session_state["items"]

# Step 3
st.divider()
step_heading("03", "Данные лота")

left_col, right_col = st.columns(2)

with left_col:
    st.text_input("Менеджер", key="fld_manager", placeholder="Введите имя...")
    st.text_input("Номер лота", key="fld_lot_number", placeholder="Введите номер лота...")

    st.text_input(
        "Дата расчёта",
        key="fld_calc_date",
        placeholder="дд.мм.гггг",
        on_change=on_calc_date_change,
    )
    if st.session_state.fld_calc_date:
        show_date_error(validate_date(st.session_state.fld_calc_date, required=True)[1])

    st.number_input(
        "Сумма дорожных расходов, тг.",
        key="fld_road_cost",
        min_value=0.0,
        step=1000.0,
        format="%.2f",
    )

with right_col:
    st.text_input("Поставщик", key="fld_supplier", placeholder="Введите поставщика...")
    st.number_input(
        "Коэффициент наценки",
        key="fld_markup_coef",
        min_value=0.01,
        step=0.05,
        format="%.2f",
    )

    st.text_input(
        "Начало лота",
        key="fld_lot_start",
        placeholder="дд.мм.гггг",
        on_change=on_lot_start_change,
    )
    if st.session_state.fld_lot_start:
        show_date_error(validate_date(st.session_state.fld_lot_start)[1])

    st.text_input(
        "Окончание лота",
        key="fld_lot_end",
        placeholder="дд.мм.гггг",
        on_change=on_lot_end_change,
    )
    if st.session_state.fld_lot_end:
        show_date_error(validate_date(st.session_state.fld_lot_end)[1])

    st.number_input(
        "Срок производства, дней",
        key="fld_lead_time_days",
        min_value=1,
        step=1,
        format="%d",
    )

usd_left, usd_right = st.columns([3.2, 1])
with usd_left:
    st.number_input(
        "Курс USD, тг.",
        key="fld_usd_rate",
        min_value=0.0,
        step=0.01,
        format="%.2f",
    )
with usd_right:
    st.markdown("<div style='height:1.75rem'></div>", unsafe_allow_html=True)
    if st.button("с Нацбанка РК", width="stretch"):
        with st.spinner("Загрузка..."):
            rate = fetch_usd_cached()
        if rate:
            st.session_state.fld_usd_rate = float(rate)
            st.toast(f"Курс USD: {rate:.2f} тг.")
        else:
            st.error("Не удалось получить курс. Попробуйте позже.")

header = sync_header_from_form()

# Generate
st.divider()

if st.button("Сформировать расчёт", type="primary", width="stretch"):
    date_errors = [
        validate_date(st.session_state.fld_calc_date, required=True)[1],
        validate_date(st.session_state.fld_lot_start)[1] if st.session_state.fld_lot_start else None,
        validate_date(st.session_state.fld_lot_end)[1] if st.session_state.fld_lot_end else None,
    ]
    date_errors = [e for e in date_errors if e]

    if date_errors:
        st.error(date_errors[0])
    elif not has_valid_items(items):
        st.error("Добавьте хотя бы одну позицию с наименованием.")
    elif header.get("usd_rate", 0) <= 0:
        st.error("Укажите курс USD (тг.).")
    elif not os.path.exists("template.xlsx"):
        st.error("Шаблон template.xlsx не найден.")
    else:
        try:
            with st.spinner("Формирую Excel..."):
                st.session_state["generated_file"] = build_excel_from_template(
                    "template.xlsx", header, items
                )
            st.session_state["generated_name"] = f"расчёт_{header['lot_number'] or 'лот'}.xlsx"
            st.success("Готово. Скачайте файл ниже.")
        except Exception as exc:
            st.error(f"Ошибка при формировании: {exc}")

if st.session_state.get("generated_file"):
    st.download_button(
        "Скачать Excel",
        data=st.session_state["generated_file"],
        file_name=st.session_state["generated_name"],
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        type="primary",
        width="stretch",
    )
