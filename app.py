"""
Heat Energy - Тендер-калькулятор на Streamlit
Переиспользует всю логику из существующих модулей
"""

import streamlit as st
from streamlit.errors import StreamlitSecretNotFoundError
import tempfile
import traceback
import os
from datetime import date
from io import BytesIO

from extract_raw import extract_any
from extract_heuristic import extract_items as extract_items_free
from extract_with_llm import extract_fields as extract_items_llm
from fetch_usd_rate import get_usd_rate
from fill_tender_template import fill_multi
import openpyxl

# ===== Конфиг Streamlit =====
st.set_page_config(
    page_title="Тендер-калькулятор",
    page_icon="📄",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ===== Кастомный CSS =====
st.markdown("""
<style>
    :root {
        --accent: #0f766e;
        --ink: #17202a;
        --muted: #5b6773;
        --line: #dde5ea;
    }

    .stApp {
        background: #f6f8fa;
        color: var(--ink);
    }

    [data-testid="stHeader"] {
        background: transparent;
    }

    .block-container {
        padding-top: 2rem;
        max-width: 1180px;
    }

    [data-testid="stSidebar"] {
        background-color: #ffffff;
        border-right: 1px solid var(--line);
    }

    .stTabs [data-baseweb="tab-list"] button {
        background-color: #ffffff;
        border: 1px solid var(--line);
        color: var(--ink);
        border-radius: 6px 6px 0 0;
    }

    .stTabs [data-baseweb="tab-list"] button[aria-selected="true"] {
        background-color: var(--accent);
        color: white;
    }

    h1, h2, h3 {
        color: var(--ink);
    }

    .stButton button {
        border-radius: 6px;
        font-weight: 600;
    }

    .app-subtitle {
        color: var(--muted);
        margin-top: -0.75rem;
    }

    .metric-line {
        background: #ffffff;
        border: 1px solid var(--line);
        border-radius: 6px;
        padding: 0.85rem 1rem;
    }
</style>
""", unsafe_allow_html=True)

# ===== Инициализация сессии =====
if "items" not in st.session_state:
    st.session_state["items"] = []
if "header" not in st.session_state:
    st.session_state["header"] = {
        "manager": "",
        "supplier": "",
        "lot_number": "",
        "calc_date": date.today().strftime("%d.%m.%Y"),
        "lot_start": "",
        "lot_end": "",
        "lead_time_days": 10,
        "markup_coef": 1.5,
        "usd_rate": 0,
        "road_cost": 0,
    }
if "raw_text" not in st.session_state:
    st.session_state["raw_text"] = ""
if "template_file" not in st.session_state:
    st.session_state["template_file"] = None

items = st.session_state["items"]
header = st.session_state["header"]

# ===== Header =====
col1, col2 = st.columns([4, 1])
with col1:
    st.markdown("# Тендер-калькулятор")
    st.markdown('<div class="app-subtitle">Загрузка спецификации, проверка позиций и выгрузка Excel-расчёта</div>', unsafe_allow_html=True)
with col2:
    st.markdown("**Heat Energy**")
    st.caption("Streamlit Cloud")

st.markdown("---")

# ===== Главная логика =====
def format_date(value: str) -> str:
    """Автоформатирование дат в дд.мм.гггг"""
    digits = ''.join(filter(str.isdigit, value))[:8]
    if len(digits) <= 2:
        return digits
    if len(digits) <= 4:
        return f"{digits[:2]}.{digits[2:]}"
    return f"{digits[:2]}.{digits[2:4]}.{digits[4:]}"

@st.cache_data
def fetch_usd_cached():
    """Кэшированное получение курса USD"""
    try:
        return get_usd_rate()
    except Exception as e:
        st.warning(f"Не удалось получить курс: {e}")
        return None

def normalize_item(i):
    return {
        "name": i.get("name") or "",
        "unit": i.get("unit") or "",
        "qty": i.get("qty") or 0,
        "unit_price": i.get("unit_price") or 0,
    }

def get_secret(name: str, default: str = "") -> str:
    try:
        return st.secrets.get(name, default)
    except StreamlitSecretNotFoundError:
        return default

# ===== Левая панель (Загрузка) =====
with st.sidebar:
    st.markdown("## Загрузка документа")
    
    uploaded_file = st.file_uploader(
        "Выберите ТЗ/спецификацию",
        type=["docx", "xlsx", "pdf"],
        help="Поддерживаются .docx, .xlsx, .pdf"
    )
    
    if uploaded_file:
        st.success(f"Загружен: {uploaded_file.name}")
        
        if st.button("Распознать позиции", use_container_width=True):
            with st.spinner("Читаю документ..."):
                with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(uploaded_file.name)[1]) as tmp:
                    tmp.write(uploaded_file.getbuffer())
                    tmp_path = tmp.name
                
                try:
                    raw_text = extract_any(tmp_path)
                    items = extract_items_free(tmp_path)
                    
                    st.session_state["raw_text"] = raw_text[:8000]
                    st.session_state["items"] = [normalize_item(i) for i in items]
                    items = st.session_state["items"]
                    
                    st.success(f"Найдено позиций: {len(items)}")
                except Exception as e:
                    st.error(f"Ошибка: {e}")
                    traceback.print_exc()
                finally:
                    os.unlink(tmp_path)
    
    st.markdown("---")
    st.markdown("## Claude")
    default_api_key = get_secret("ANTHROPIC_API_KEY")
    api_key = st.text_input(
        "Anthropic API ключ",
        value=default_api_key,
        type="password",
        help="Для более точного распознавания",
    )
    
    if api_key and st.session_state["raw_text"] and st.button("Распознать через Claude", use_container_width=True):
        with st.spinner("Claude анализирует документ..."):
            try:
                result = extract_items_llm(st.session_state["raw_text"], api_key=api_key)
                st.session_state["items"] = [normalize_item(i) for i in result.get("items", [])]
                items = st.session_state["items"]
                st.success(f"Claude нашёл позиций: {len(items)}")
            except Exception as e:
                st.error(f"Ошибка LLM: {e}")
    
    st.markdown("---")
    st.markdown("## Шаблон Excel")
    template_file = st.file_uploader("Шаблон Excel", type=["xlsx"], key="template_upload")
    if template_file:
        st.session_state["template_file"] = template_file
        st.success(f"Шаблон: {template_file.name}")

# ===== Основной контент (3 вкладки) =====
tab1, tab2, tab3 = st.tabs(["Позиции", "Данные лота", "Формирование"])

# ===== TAB 1: Позиции =====
with tab1:
    st.markdown("### Позиции")
    
    col1, col2 = st.columns([0.78, 0.22])
    
    with col1:
        if items:
            # Показываем редактируемые поля
            for idx, item in enumerate(items):
                with st.expander(f"Позиция {idx+1}: {item['name'][:40] or 'без названия'}", expanded=False):
                    col_a, col_b, col_c, col_d = st.columns(4)
                    
                    with col_a:
                        items[idx]["name"] = st.text_input(
                            "Наименование",
                            value=item["name"],
                            key=f"name_{idx}"
                        )
                    
                    with col_b:
                        items[idx]["unit"] = st.text_input(
                            "Ед. изм.",
                            value=item["unit"],
                            key=f"unit_{idx}"
                        )
                    
                    with col_c:
                        items[idx]["qty"] = st.number_input(
                            "Кол-во",
                            value=float(item["qty"]) if item["qty"] else 0,
                            key=f"qty_{idx}"
                        )
                    
                    with col_d:
                        items[idx]["unit_price"] = st.number_input(
                            "Цена DDP (₸)",
                            value=float(item["unit_price"]) if item["unit_price"] else 0,
                            key=f"price_{idx}"
                        )
                    
                    if st.button("Удалить", key=f"del_{idx}"):
                        items.pop(idx)
                        st.rerun()
        else:
            st.info("Загрузите документ в левой панели или добавьте позицию вручную.")
    
    with col2:
        if st.button("Добавить позицию", use_container_width=True):
            items.append({
                "name": "",
                "unit": "",
                "qty": 0,
                "unit_price": 0,
            })
            st.rerun()
        
        st.markdown(f'<div class="metric-line"><b>Позиций</b><br>{len(items)}</div>', unsafe_allow_html=True)

# ===== TAB 2: Данные лота =====
with tab2:
    st.markdown("### Заполните данные лота")
    
    col1, col2 = st.columns(2)
    
    with col1:
        header["manager"] = st.text_input(
            "Менеджер",
            value=header["manager"],
            placeholder="Батыр"
        )
        header["supplier"] = st.text_input(
            "Поставщик",
            value=header["supplier"],
            placeholder="RG GOLD"
        )
        header["lot_number"] = st.text_input(
            "Номер лота",
            value=header["lot_number"],
            placeholder="T-0003701"
        )
        header["markup_coef"] = st.number_input(
            "Коэффициент наценки",
            value=header["markup_coef"],
            step=0.05
        )
    
    with col2:
        calc_date = st.text_input(
            "Дата расчёта",
            value=header["calc_date"],
            placeholder="дд.мм.гггг"
        )
        header["calc_date"] = format_date(calc_date)
        
        lot_start = st.text_input(
            "Начало лота",
            value=header["lot_start"],
            placeholder="дд.мм.гггг"
        )
        header["lot_start"] = format_date(lot_start)
        
        lot_end = st.text_input(
            "Окончание лота",
            value=header["lot_end"],
            placeholder="дд.мм.гггг"
        )
        header["lot_end"] = format_date(lot_end)
        
        header["lead_time_days"] = st.number_input(
            "Срок производства, дней",
            value=header["lead_time_days"]
        )
    
    st.markdown("---")
    
    col1, col2 = st.columns(2)
    with col1:
        header["road_cost"] = st.number_input(
            "Сумма дорожных расходов (₸)",
            value=header["road_cost"],
            step=0.01
        )
    
    with col2:
        usd_rate = st.number_input(
            "Курс USD",
            value=header["usd_rate"],
            step=0.01,
            placeholder="486.19"
        )
        header["usd_rate"] = usd_rate
        
        if st.button("Получить с Нацбанка РК", use_container_width=True):
            with st.spinner("Получаю курс..."):
                rate = fetch_usd_cached()
                if rate:
                    header["usd_rate"] = rate
                    st.success(f"Курс USD: {rate}")
                    st.rerun()

# ===== TAB 3: Формирование =====
with tab3:
    st.markdown("### Формирование расчёта")
    
    # Проверка заполнения
    col1, col2 = st.columns(2)
    with col1:
        st.info(f"Позиций: {len(items)}")
    with col2:
        if header["usd_rate"] > 0:
            st.success(f"Курс USD: {header['usd_rate']}")
        else:
            st.warning("Укажите курс USD")
    
    st.markdown("---")
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("Скачать Excel", use_container_width=True, type="primary"):
            # Проверки
            if not items or not any(i["name"] for i in items):
                st.error("Добавьте хотя бы одну позицию")
            elif header["usd_rate"] <= 0:
                st.error("Укажите курс USD")
            else:
                # Проверяем наличие шаблона
                if not os.path.exists("template.xlsx"):
                    st.error("Шаблон template.xlsx не найден в папке приложения")
                else:
                    with st.spinner("Генерирую Excel..."):
                        try:
                            # Подготавливаем данные
                            payloadItems = [
                                {
                                    "item_name": i["name"],
                                    "qty": i["qty"],
                                    "purchase_price_ddp": i["unit_price"],
                                }
                                for i in items
                                if i["name"] and i["name"].strip()
                            ]
                            
                            with tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx") as tmp:
                                out_path = tmp.name

                            try:
                                fill_multi("template.xlsx", out_path, header, payloadItems)
                                with open(out_path, "rb") as f:
                                    file_data = f.read()
                            finally:
                                if os.path.exists(out_path):
                                    os.unlink(out_path)
                            
                            # Скачивание
                            st.download_button(
                                label="Скачать расчёт",
                                data=file_data,
                                file_name=f"расчёт_{header['lot_number'] or 'лот'}.xlsx",
                                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                            )
                            
                            st.success("Файл готов к скачиванию.")
                        except Exception as e:
                            st.error(f"Ошибка: {e}")
                            traceback.print_exc()
    
    with col2:
        if st.button("Скачать через загруженный шаблон", use_container_width=True):
            template_file = st.session_state["template_file"]
            if not template_file:
                st.warning("Выберите шаблон в левой панели")
            elif not items or not any(i["name"] for i in items):
                st.error("Добавьте хотя бы одну позицию")
            elif header["usd_rate"] <= 0:
                st.error("Укажите курс USD")
            else:
                with st.spinner("Генерирую Excel..."):
                    try:
                        # Чтение шаблона
                        wb = openpyxl.load_workbook(BytesIO(template_file.getbuffer()))
                        ws = wb["расчет"] if "расчет" in wb.sheetnames else wb[wb.sheetnames[0]]
                        
                        # Заполнение
                        ws["B2"] = header["manager"]
                        ws["B3"] = header["supplier"]
                        ws["R2"] = f'лот {header["lot_number"]}'
                        ws["B4"] = f'Дата:{header["calc_date"]}'
                        ws["B5"] = f'Дата начала лота:{header["lot_start"]}'
                        ws["B6"] = f'Дата окончания лота: {header["lot_end"]}'
                        ws["B7"] = f'Срок производства: {header["lead_time_days"]} дн'
                        ws["J9"] = header["markup_coef"]
                        ws["K9"] = header["usd_rate"]
                        ws["H18"] = header["road_cost"]
                        
                        first_row = 12
                        for i, item in enumerate(items):
                            if item["name"]:
                                r = first_row + i
                                ws[f"B{r}"] = i + 1
                                ws[f"C{r}"] = item["name"]
                                ws[f"D{r}"] = item["qty"]
                                ws[f"E{r}"] = item["unit_price"]
                        
                        # Скачивание
                        output = BytesIO()
                        wb.save(output)
                        output.seek(0)
                        
                        st.download_button(
                            label="Скачать расчёт",
                            data=output.getvalue(),
                            file_name=f"расчёт_{header['lot_number'] or 'лот'}.xlsx",
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                        )
                        
                        st.success("Файл готов.")
                    except Exception as e:
                        st.error(f"Ошибка: {e}")

st.markdown("---")
st.markdown("""
<div style="text-align:center;color:#999;font-size:11px;margin-top:30px;">
Heat Energy Tender Calculator · Streamlit Cloud
</div>
""", unsafe_allow_html=True)
