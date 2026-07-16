"""Heat Energy - Streamlit tender calculator."""

import base64
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
from fill_tender_template import fill_lots_kz, fill_lots_foreign


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
    --ink: #14213f;
    --ink-soft: #55658c;
    --paper: #f4f8ff;
    --paper-2: #e7f0ff;
    --line: #c9dbf7;
    --teal: #1c6fe0;
    --teal-deep: #0d3f92;
    --ember: #17a3f5;
    --ember-soft: #7cc9fb;
  }

  .stApp {
    background-color: #0a1220;
    background-image:
      radial-gradient(ellipse 80% 60% at 12% 15%, rgba(28, 111, 224, 0.26) 0%, transparent 55%),
      radial-gradient(ellipse 65% 55% at 88% 80%, rgba(23, 163, 245, 0.16) 0%, transparent 52%),
      linear-gradient(160deg, #0a1220 0%, #0e1c38 40%, #142b52 75%, #0a1626 100%);
    background-attachment: fixed;
    font-family: "Inter", sans-serif;
  }

  header[data-testid="stHeader"] { background: transparent; }
  [data-testid="stSidebar"], [data-testid="collapsedControl"] { display: none; }
  /* Streamlit's own toolbar (Deploy button + the "⋮" main-menu icon) is a
     separate, higher-stacked layer pinned to the same top-right corner our
     own header row lives in - background:transparent above only hid the
     bar's fill, not its buttons, so the menu icon floated over our reset
     button as three stray dashes. This app has its own branded chrome, so
     Streamlit's is just noise here - hide it outright rather than fight
     its z-index. */
  [data-testid="stToolbar"] { display: none !important; }

  div.block-container {
    position: relative;
    background: linear-gradient(180deg, var(--paper) 0%, var(--paper-2) 100%);
    border-radius: 14px;
    /* clamp() instead of fixed rem values: padding eases off on narrow
       viewports instead of eating into the usable width, and max-width
       backs off from a hard 960px so the card never touches the edges on
       medium-width windows or phones. */
    padding: clamp(1rem, 3vw, 1.4rem) clamp(1rem, 4vw, 2.25rem) clamp(1.4rem, 4vw, 2.5rem);
    margin-top: 0.15rem;
    max-width: min(960px, 94vw);
    box-shadow:
      0 2px 0 rgba(255, 255, 255, 0.5) inset,
      0 32px 64px rgba(0, 0, 0, 0.45),
      0 8px 24px rgba(0, 0, 0, 0.25);
    color: var(--ink);
  }
  /* full-width gradient band across the top of the card, echoed as a
     subtle glow behind the brand mark so the header reads as one piece */
  div.block-container::before {
    content: "";
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    height: 7px;
    border-radius: 14px 14px 0 0;
    background: linear-gradient(90deg, var(--teal) 0%, var(--ember-soft) 50%, var(--teal) 100%);
  }

  h1, h2, h3 { color: var(--ink) !important; }

  .app-header-row {
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    flex-wrap: wrap;
    gap: 0.6rem 1.25rem;
    margin-bottom: 0.35rem;
    padding-top: 0.2rem;
  }
  .brand-row {
    display: flex;
    align-items: center;
    gap: 0.75rem;
    margin: 0 0 0.3rem;
  }
  .brand-row img {
    width: 3rem;
    height: 3rem;
    flex-shrink: 0;
    display: block;
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
  div[data-testid="stNumberInput"] label,
  div[data-testid="stDateInput"] label,
  div[data-testid="stSelectbox"] label {
    font-size: 0.84rem !important;
    font-weight: 500 !important;
    color: var(--ink-soft) !important;
  }
  div[data-testid="stTextInput"] input,
  div[data-testid="stNumberInput"] input,
  div[data-testid="stDateInput"] input,
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
  div[data-testid="stDateInput"] input:focus,
  div[data-testid="stTextArea"] textarea:focus {
    border-color: var(--ember) !important;
    box-shadow: 0 0 0 1px var(--ember) !important;
  }
  /* "Валюта закупки" selectbox: without this it keeps Streamlit's theme
     secondaryBackgroundColor (a pale blue), which reads as an odd, unrelated
     tint sitting right next to the plain-white text/number/date fields
     around it. Matched to the same white + var(--line) treatment as those. */
  div[data-testid="stSelectbox"] > div > div {
    border-radius: 7px !important;
    border-color: var(--line) !important;
    background: #fff !important;
  }
  div[data-testid="stSelectbox"] > div > div:hover {
    border-color: var(--ember) !important;
  }
  div[data-testid="stSelectbox"] span {
    color: var(--ink) !important;
    font-family: "IBM Plex Mono", monospace;
    font-size: 0.9rem;
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
    background: #eef6ff !important;
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
    box-shadow: 0 4px 14px rgba(28, 111, 224, 0.35) !important;
  }
  .stButton > button[kind="primary"]:hover,
  div[data-testid="stDownloadButton"] > button[kind="primary"]:hover {
    color: #fff !important;
    box-shadow: 0 4px 16px rgba(23, 163, 245, 0.45) !important;
  }
  .stButton > button:disabled {
    opacity: 0.65 !important;
    background: #dbe6f7 !important;
    color: var(--ink-soft) !important;
    border: 1px dashed var(--line) !important;
  }

  [data-testid="stToast"] { font-family: "Inter", sans-serif; }

  /* Reset icon buttons (Material "restart_alt" icon, no text label) -
     square and consistently sized, distinct from the full-width text
     buttons elsewhere (Добавить лот, Сформировать, etc.). Targeted via
     st.container(key=...) wrapper classes rather than button content (CSS
     can't select on text), matched by prefix since the per-lot ones carry
     a dynamic lot id suffix. Sized to roughly match the badge's own height
     (padding 0.5rem*2 + its two text lines) so the header row reads as one
     aligned unit instead of a tiny button dwarfed by its neighbours. */
  .st-key-header_reset_btn button,
  [class*="st-key-icon_reset_items_"] button,
  [class*="st-key-icon_reset_header_"] button {
    width: 2.6rem !important;
    height: 2.6rem !important;
    min-width: 2.6rem !important;
    padding: 0 !important;
    display: flex !important;
    align-items: center !important;
    justify-content: center !important;
  }
  .st-key-header_reset_btn button span[data-testid="stIconMaterial"],
  [class*="st-key-icon_reset_items_"] button span[data-testid="stIconMaterial"],
  [class*="st-key-icon_reset_header_"] button span[data-testid="stIconMaterial"] {
    font-size: 1.2rem !important;
    color: var(--teal-deep) !important;
  }
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
    background: #eaf3ff;
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
LOGO_PATH = os.path.join(os.path.dirname(__file__), "assets", "logo.png")


@st.cache_data(show_spinner=False)
def load_logo_b64(path: str) -> str:
    """Inlined as a data URI in the header markup - simplest way to embed a
    local image inside raw st.markdown HTML (no static-file server to set
    up, works the same locally and on Streamlit Cloud)."""
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode("ascii")


def init_state() -> None:
    st.session_state.setdefault("lot_type", "kz")
    st.session_state.setdefault("lot_ids_kz", [0])
    st.session_state.setdefault("lot_ids_foreign", [0])
    st.session_state.setdefault("next_lot_id_kz", 1)
    st.session_state.setdefault("next_lot_id_foreign", 1)
    st.session_state.setdefault("active_lot_kz", 0)
    st.session_state.setdefault("active_lot_foreign", 0)
    st.session_state.setdefault("raw_text", "")
    st.session_state.setdefault("generated_file", None)
    st.session_state.setdefault("generated_name", "расчёт.xlsx")


def normalize_item_kz(item: dict) -> dict:
    return {
        "name": str(item.get("name") or "").strip(),
        # qty=0 on a named row used to be allowed, which is harmless in the
        # kz template (nothing divides by quantity there) but produces a
        # #DIV/0! in the foreign template (see normalize_item_fx) - clamped
        # to 1 in both for consistency, and because "0 of an item" isn't a
        # meaningful line anyway.
        "qty": max(1, int(item.get("qty") or 1)),
        "purchase_price_ddp": max(0.0, float(item.get("purchase_price_ddp") or 0)),
        "extra_cost": max(0.0, float(item.get("extra_cost") or 0)),
    }


def normalize_item_fx(item: dict) -> dict:
    return {
        "name": str(item.get("name") or "").strip(),
        "unit": str(item.get("unit") or "").strip(),
        # qty=0 here used to reach the foreign template's H/R columns, both
        # of which divide by quantity per item (=.../E12) - a named row with
        # qty=0 would generate a #DIV/0! in Excel. Minimum 1, same reasoning
        # as truck_count below.
        "qty": max(1, int(item.get("qty") or 1)),
        "price_fca": max(0.0, float(item.get("price_fca") or 0)),
        "sale_price_kzt": max(0.0, float(item.get("sale_price_kzt") or 0)),
        "duty_rate_pct": max(0.0, float(item.get("duty_rate_pct") or 0)),
        "truck_count": max(1, int(item.get("truck_count") or 1)),
        "overhead": max(0.0, float(item.get("overhead") or 0)),
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


def step_heading(number: str, title: str) -> None:
    st.markdown(
        f'<p class="step-title"><span class="num">{number}</span>{title}</p>',
        unsafe_allow_html=True,
    )


def fmt_date(value) -> str:
    return value.strftime("%d.%m.%Y") if value else ""


init_state()
# Reading the RADIO WIDGET'S OWN key here (before the radio itself is even
# rendered further down) is intentional, not a mistake: Streamlit applies a
# widget's new value to session_state as soon as the click is processed -
# before the script starts running - so this already reflects the current
# click. st.session_state["lot_type"] (a separate mirror variable, set only
# once the script reaches the "Тип лота" section below) would instead still
# hold the *previous* run's value at this point, which is exactly what made
# the "Лотов в тендере" badge show the other tab's count for one render
# after switching.
lot_type = ("foreign"
            if st.session_state.get("fld_lot_type_radio", "Казахстан → Казахстан") != "Казахстан → Казахстан"
            else "kz")
st.session_state["lot_type"] = lot_type
lot_type_key = f"lot_ids_{lot_type}"


def reset_full_form() -> None:
    """on_click, not inline - clears session_state entirely before the next
    rerun. init_state() (called at module top-level on every run) only uses
    setdefault(), so without wiping the keys here first the 'reset' would be
    a no-op: every value would already exist and setdefault would leave it
    untouched."""
    for _key in list(st.session_state.keys()):
        del st.session_state[_key]


def start_reset_confirm() -> None:
    st.session_state["confirm_reset_all"] = True


def cancel_reset_confirm() -> None:
    st.session_state["confirm_reset_all"] = False


st.session_state.setdefault("confirm_reset_all", False)

# ------------------------------------------------- Плавающий калькулятор ---
# Обычный арифметический калькулятор "для прикидок", не связанный с бизнес-
# логикой формы.
#
# Earlier versions positioned the IFRAME itself with position:fixed (via
# window.frameElement) and resized it to match its own content. That broke
# on at least one real laptop - "калькулятор пропал, не вижу его" - and the
# likely reason is a well-known CSS trap: position:fixed stops being fixed
# to the *viewport* and instead becomes fixed to the nearest ancestor that
# has a `transform`/`filter`/`perspective`/`will-change` set, and Streamlit's
# own component-mounting machinery is exactly the kind of code that sets
# `transform` on wrapper divs for its mount/fade transitions. Depending on
# which ancestor picks that up, the iframe (and everything positioned
# relative to it) can end up parked off-screen or clipped - invisible, with
# no error anywhere, and not reproducible on every machine.
#
# The fix: don't fight the iframe's own ancestry at all. Build the
# calculator once and append it as a direct child of window.parent.document
# body - the top-level page, not nested inside any Streamlit component
# wrapper - so position:fixed has nothing above it to get hijacked by. The
# iframe itself goes back to being a normal, invisible, zero-footprint
# script loader (height=1, never resized/repositioned), which also means
# the old "dead click zone" problem structurally can't recur - there's
# nothing iframe-shaped covering the page anymore, ever.
st.iframe(
    r"""
<script>
(function () {
  try {
    var doc = window.parent.document;
    if (doc.getElementById('calc-shell')) { return; }

    var style = doc.createElement('style');
    style.textContent = `
      #calc-shell { position: fixed; top: 110px; right: 22px; z-index: 999999;
        font-family: Inter, sans-serif; }
      #calc-box { width: 220px; background: linear-gradient(180deg,#f4f8ff,#e7f0ff);
        border: 1px solid #c9dbf7; border-radius: 10px;
        box-shadow: 0 12px 28px rgba(0,0,0,0.35); overflow: hidden; }
      #calc-head { display:flex; justify-content:space-between; align-items:center;
        background:#1c6fe0; color:#fff; font-size:12.5px; font-weight:600;
        padding:6px 10px; cursor:pointer; user-select:none; }
      #calc-toggle { opacity:0.85; }
      #calc-screen { font-family:"IBM Plex Mono",monospace; text-align:right;
        font-size:20px; padding:10px 12px; color:#14213f; background:#fff;
        border-bottom:1px solid #c9dbf7; overflow:hidden; text-overflow:ellipsis; }
      #calc-grid { display:grid; grid-template-columns:repeat(4,1fr); gap:1px;
        background:#c9dbf7; }
      #calc-grid button { border:none; background:#fff; padding:11px 0;
        font-size:14.5px; color:#14213f; cursor:pointer; font-family:Inter,sans-serif; }
      #calc-grid button:hover { background:#eaf4ff; }
      #calc-grid button.op { background:#e7f0ff; color:#1c6fe0; font-weight:600; }
      #calc-grid button.eq { background:#17a3f5; color:#fff; font-weight:700; grid-column: span 3; }
      #calc-grid button.eq:hover { background:#0f86d0; }
      #calc-body.collapsed { display:none; }
    `;
    doc.head.appendChild(style);

    var shell = doc.createElement('div');
    shell.id = 'calc-shell';
    shell.innerHTML =
      '<div id="calc-box">' +
        '<div id="calc-head">' +
          '<span>Калькулятор</span><span id="calc-toggle">▸</span>' +
        '</div>' +
        '<div id="calc-body" class="collapsed">' +
          '<div id="calc-screen">0</div>' +
          '<div id="calc-grid"></div>' +
        '</div>' +
      '</div>';
    doc.body.appendChild(shell);

    var screen = shell.querySelector('#calc-screen');
    var grid = shell.querySelector('#calc-grid');
    var body = shell.querySelector('#calc-body');
    var toggle = shell.querySelector('#calc-toggle');
    var head = shell.querySelector('#calc-head');
    var keys = ['(',')','C','⌫', '7','8','9','÷', '4','5','6','×', '1','2','3','-', '0','00','.','+', '%','='];
    var expr = '';

    // Раздельные разряды пробелом при отображении ("500 000" вместо "500000"),
    // чтобы с одного взгляда отличить 500 тысяч от 5 миллионов - как и везде
    // в форме. Форматируется только ЭКРАН: сама expr остаётся "чистой"
    // строкой без пробелов, поэтому на вычисления (и на то, что попадёт в
    // регэксп-проверку безопасности перед eval) это не влияет.
    function formatNumber(numStr) {
      var parts = numStr.split('.');
      var intPart = parts[0].replace(/\B(?=(\d{3})+(?!\d))/g, ' ');
      return parts.length > 1 ? intPart + '.' + parts[1] : intPart;
    }

    function formatExpr(str) {
      return str.replace(/\d+(\.\d*)?/g, function (m) { return formatNumber(m); });
    }

    function render() { screen.textContent = expr === '' ? '0' : formatExpr(expr); }

    function press(k) {
      if (k === 'C') { expr = ''; }
      else if (k === '⌫') { expr = expr.slice(0, -1); }
      else if (k === '=') {
        try {
          var safe = expr.replace(/×/g, '*').replace(/÷/g, '/').replace(/%/g, '/100');
          if (!/^[0-9+\-*/.() ]*$/.test(safe)) throw new Error('bad');
          var result = Function('"use strict"; return (' + safe + ')')();
          expr = String(Math.round(result * 1e8) / 1e8);
        } catch (e) { expr = 'Ошибка'; }
      } else { expr = (expr === 'Ошибка' ? '' : expr) + k; }
      render();
    }

    keys.forEach(function (k) {
      var btn = doc.createElement('button');
      btn.textContent = k;
      if (['÷','×','-','+','%'].includes(k)) btn.className = 'op';
      if (k === '=') btn.className = 'eq';
      btn.onclick = function () { press(k); };
      grid.appendChild(btn);
    });

    // Starts collapsed (see the markup above) so it never covers more of
    // the page than the small header pill until the user explicitly opens
    // it - matters even more now that nothing needs to be resized to
    // achieve that, it's just the element's natural collapsed height.
    head.addEventListener('click', function () {
      var collapsed = body.classList.toggle('collapsed');
      toggle.textContent = collapsed ? '▸' : '▾';
    });
  } catch (e) {}
})();
</script>
""",
    height=1,
)

# ------------------------------------------ Автовыделение чисел в полях ---
# st.number_input, в отличие от табличных редакторов, не выделяет текущее
# значение при клике/фокусе - приходится сначала вручную стирать то, что
# там уже написано (например "0"), и только потом печатать своё. Родного
# параметра под это в Streamlit нет, поэтому вешаем делегированный
# обработчик на document родительского окна - тот же приём, что и у
# калькулятора ниже (iframe того же происхождения, доступ разрешён).
# Обработчик висит на document, а не на конкретных полях, поэтому
# переживает любые перерисовки Streamlit (поля в DOM пересоздаются -
# слушатель на их родителе остаётся).
st.iframe(
    """
<script>
(function () {
  try {
    var doc = window.parent.document;
    doc.addEventListener('focusin', function (e) {
      var el = e.target;
      if (el && el.tagName === 'INPUT' &&
          el.closest('[data-testid="stNumberInput"]')) {
        el.select();
      }
    });
  } catch (e) {}
})();
</script>
""",
    height=1,
)

# --------------------------------------------- Русские месяцы в календаре --
# st.date_input's calendar popup (BaseWeb) has no locale setting exposed
# from Python - it always renders English month/weekday names. The popup is
# torn down and rebuilt from scratch every time it opens (and again on every
# month/year navigation click), so a one-off translation right after load
# wouldn't survive the first click - a MutationObserver re-translates it on
# every redraw instead. Same-origin iframe access as the other utility
# scripts here, so no CSP/cross-origin issue.
st.iframe(
    r"""
<script>
(function () {
  try {
    var doc = window.parent.document;
    if (doc.__ruCalendarObserverInstalled) { return; }
    doc.__ruCalendarObserverInstalled = true;

    var MONTHS = {
      'January': 'Январь', 'February': 'Февраль', 'March': 'Март', 'April': 'Апрель',
      'May': 'Май', 'June': 'Июнь', 'July': 'Июль', 'August': 'Август',
      'September': 'Сентябрь', 'October': 'Октябрь', 'November': 'Ноябрь', 'December': 'Декабрь'
    };
    var WEEKDAYS = {
      'Monday': 'Пн', 'Tuesday': 'Вт', 'Wednesday': 'Ср', 'Thursday': 'Чт',
      'Friday': 'Пт', 'Saturday': 'Сб', 'Sunday': 'Вс'
    };

    function translateMonthButton(btn) {
      // The month/year header buttons share markup; only the month one's
      // direct text node matches a key in MONTHS, so the year button (just
      // digits) is naturally left alone without special-casing it.
      for (var i = 0; i < btn.childNodes.length; i++) {
        var node = btn.childNodes[i];
        if (node.nodeType === 3) {
          var text = node.textContent.trim();
          if (MONTHS[text]) { node.textContent = MONTHS[text]; }
          break;
        }
      }
    }

    function translateCalendars() {
      doc.querySelectorAll('[data-baseweb="calendar"] button[aria-haspopup="true"]')
        .forEach(translateMonthButton);
      doc.querySelectorAll('[data-baseweb="calendar"] div[alt]').forEach(function (el) {
        var ru = WEEKDAYS[el.getAttribute('alt')];
        if (ru && el.textContent !== ru) { el.textContent = ru; }
      });
      // The month-picker dropdown (opened by clicking the month button) is
      // a <ul role="listbox"> rendered in its own portal, not nested under
      // [data-baseweb="calendar"] - matched globally instead. Selectboxes
      // elsewhere in the app (currency, lot type) use the same role but
      // their options never match an English month name, so this is safe.
      doc.querySelectorAll('ul[role="listbox"] li[role="option"]').forEach(function (li) {
        var text = li.textContent.trim();
        if (MONTHS[text]) { li.textContent = MONTHS[text]; }
      });
    }

    translateCalendars();
    new MutationObserver(translateCalendars)
      .observe(doc.body, { childList: true, subtree: true, characterData: true });
  } catch (e) {}
})();
</script>
""",
    height=1,
)

# ---------------------------------------------------------------- Header ---
# Split across real st.columns (rather than one raw-HTML flex row) so the
# reset icon button - a genuine widget - can sit directly next to the
# "Лотов в тендере" badge without resorting to absolute-position CSS hacks
# to fake alignment with markup it isn't actually a DOM sibling of.
# vertical_alignment="center" matters here: the title column is two lines
# tall (title + subtitle) while the badge/button are single-line, so "top"
# alignment left them visually stranded near the top edge instead of
# centered against the header block they belong to.
_logo_b64 = load_logo_b64(LOGO_PATH)
title_col, badge_col, reset_col = st.columns([5, 1.5, 0.7], vertical_alignment="center")
with title_col:
    st.markdown(
        f"""
<div class="app-header-main">
  <div class="brand-row">
    <img src="data:image/png;base64,{_logo_b64}" alt="Heat Energy" />
    <h1>Heat Energy<span class="dot">.</span> Tender Calculator</h1>
  </div>
  <p class="app-header-sub">Калькулятор тендерных расчётов и подготовки Excel</p>
</div>
""",
        unsafe_allow_html=True,
    )
with badge_col:
    st.markdown(
        f"""
<div class="hdr-badge">
  <span class="hdr-badge-label">Лотов в тендере</span>
  <span class="hdr-badge-value">{len(st.session_state[lot_type_key])}</span>
</div>
""",
        unsafe_allow_html=True,
    )
with reset_col:
    with st.container(key="header_reset_btn"):
        # icon=":material/..." renders one of Streamlit's built-in Material
        # Symbols as a crisp inline SVG - unlike an emoji glyph, it doesn't
        # depend on the OS/browser having a matching emoji font installed,
        # and it matches the flat, monochrome icon language the rest of the
        # app already uses (calculator, buttons) instead of standing out.
        st.button("", key="btn_reset_all_start", icon=":material/restart_alt:",
                  on_click=start_reset_confirm,
                  help="Начать новый тендер (очистить всё)")

if st.session_state["confirm_reset_all"]:
    st.warning("Все лоты, позиции и данные текущего тендера будут удалены "
               "без возможности восстановления. Скачали Excel? Тогда можно очищать.")
    confirm_col, cancel_col, _spacer_col = st.columns([1, 1, 3])
    with confirm_col:
        st.button("Да, очистить всё", key="btn_reset_all_confirm", type="primary",
                   width="stretch", on_click=reset_full_form)
    with cancel_col:
        st.button("Отмена", key="btn_reset_all_cancel", width="stretch",
                   on_click=cancel_reset_confirm)

st.divider()

# ------------------------------------------------------- Step 0: тип лота --
step_heading("01", "Тип лота")
st.radio(
    "Тип лота", ["Казахстан → Казахстан", "Закупка за рубежом → Казахстан"],
    key="fld_lot_type_radio", horizontal=True, label_visibility="collapsed",
)

lot_ids_key = f"lot_ids_{lot_type}"
next_id_key = f"next_lot_id_{lot_type}"
active_key = f"active_lot_{lot_type}"
if st.session_state[active_key] not in st.session_state[lot_ids_key]:
    st.session_state[active_key] = st.session_state[lot_ids_key][0]

# ------------------------------------------------------------ Step: лоты ---
st.divider()
step_heading("02", "Лоты тендера")
st.caption("Один тендер может включать несколько лотов — каждый лот получает "
           "свой собственный блок расчёта (шапка + позиции + итоги), они "
           "печатаются один под другим в одном Excel-файле.")


def add_lot() -> None:
    new_id = st.session_state[next_id_key]
    st.session_state[lot_ids_key].append(new_id)
    st.session_state[next_id_key] = new_id + 1
    st.session_state[active_key] = new_id


def remove_lot(lot_id: int) -> None:
    ids = st.session_state[lot_ids_key]
    if len(ids) <= 1:
        return
    ids.remove(lot_id)
    if st.session_state[active_key] == lot_id:
        st.session_state[active_key] = ids[0]
    # lot_id is never reused (next_lot_id only ever increases), so leaving
    # this behind wouldn't cause a data mix-up with a future lot - it's pure
    # housekeeping so session_state doesn't grow unbounded over a long
    # session with a lot of add/remove churn.
    st.session_state.get(f"lot_header_store_{lot_type}", {}).pop(lot_id, None)
    for _prefix in (f"items_{lot_type}_", f"items_{lot_type}_editor_", f"items_{lot_type}_seed_"):
        st.session_state.pop(f"{_prefix}{lot_id}", None)


lot_ids = st.session_state[lot_ids_key]
# st.pills is one widget with its own managed state, not N separate
# st.button()s laid out in st.columns() - the earlier button-row version
# was flaky (stale highlight for one render after a click, occasional
# missed clicks when the column count changed on add/remove) because it
# hand-rolled selection state instead of using a widget built for it.
# required=True means a lot is always selected - there is never "no active
# lot" to handle.
st.pills(
    "Лот", options=lot_ids, format_func=lambda lid: f"Лот {lot_ids.index(lid) + 1}",
    key=active_key, selection_mode="single", required=True,
    label_visibility="collapsed",
)
active_id = st.session_state[active_key]

add_col, remove_col = st.columns(2)
with add_col:
    st.button("+ Добавить лот", key=f"btn_add_lot_{lot_type}",
              on_click=add_lot, width="stretch")
with remove_col:
    st.button(f"Удалить лот {lot_ids.index(active_id) + 1}", key=f"btn_remove_lot_{lot_type}",
              on_click=remove_lot, args=(active_id,),
              disabled=len(lot_ids) <= 1, width="stretch")


def k(field: str) -> str:
    """Ключ виджета для поля `field` активного лота. Индексируется по
    стабильному lot_id (не по позиции в списке!), поэтому добавление и
    удаление лотов никогда не путает состояние виджетов между лотами -
    ровно та же причина, по которой раньше терялись данные в таблице
    позиций при слишком быстром вводе (см. items_*_editor ниже)."""
    return f"lot_{lot_type}_{active_id}_{field}"


def default_lot_header(for_type: str) -> dict:
    """Единственное место, где перечислены дефолты полей шапки лота -
    используется и при создании нового лота, и кнопкой «Сбросить» ниже,
    чтобы эти два места не могли разойтись."""
    defaults = {
        "manager": "", "supplier": "", "lot_number": "",
        "calc_date": date.today(), "lot_start": None, "lot_end": None,
        "lead_time_days": 10, "markup_coef": 1.5 if for_type == "kz" else 1.2,
        "road_cost": 0.0, "usd_rate": 0.0,
    }
    if for_type == "foreign":
        defaults.update(
            {"delivery_days": 30, "vat_rate": 16.0, "currency": "USD", "fx_rate": 0.0})
    return defaults


# Streamlit quietly discards a widget's session_state value once that
# widget stops being instantiated in a script run (its internal "stale
# widget" cleanup - see _remove_stale_widgets in Streamlit's own
# session_state.py). Since only the ACTIVE lot's header widgets render each
# run, switching away from a lot and back used to reset every field on it
# straight back to blank/default - the widget's own key was never a safe
# place to durably keep a lot's data. lot_header_store is a plain dict (not
# itself ever passed as a widget key) that isn't subject to that cleanup;
# widgets are (re-)seeded from it below and synced back into it once they've
# rendered (see the sync block right after the currency/rate section).
# Exactly the same reasoning that already made the items table resilient to
# this - see items_seed_key elsewhere in this file.
lot_header_store_key = f"lot_header_store_{lot_type}"
st.session_state.setdefault(lot_header_store_key, {})
lot_header_store = st.session_state[lot_header_store_key]
if active_id not in lot_header_store:
    lot_header_store[active_id] = default_lot_header(lot_type)

for _field, _default in lot_header_store[active_id].items():
    st.session_state.setdefault(k(_field), _default)

items_state_key = f"items_{lot_type}_{active_id}"
items_editor_key = f"items_{lot_type}_editor_{active_id}"
items_seed_key = f"items_{lot_type}_seed_{active_id}"
st.session_state.setdefault(items_state_key, [])


def reset_lot_header() -> None:
    """on_click, not inline logic - by the time a button placed after these
    widgets could run inline code, the widgets have already been instantiated
    this script run and directly overwriting their session_state keys would
    raise a StreamlitAPIException. on_click callbacks run before the rerun
    that re-instantiates them, so it's the safe place to reset a widget's
    backing value (same pattern as add_lot/remove_lot/on_fetch_rate)."""
    defaults = default_lot_header(lot_type)
    lot_header_store[active_id] = defaults
    for _field, _value in defaults.items():
        st.session_state[k(_field)] = _value


def reset_items() -> None:
    """Same on_click timing requirement as reset_lot_header - items_editor_key
    is itself a data_editor widget key."""
    st.session_state[items_state_key] = []
    st.session_state.pop(items_seed_key, None)
    st.session_state.pop(items_editor_key, None)

# ------------------------------------------------- Step 1: загрузка файла --
st.divider()
step_heading("03", f"Загрузите документ для лота {lot_ids.index(active_id) + 1}")
st.markdown('<div class="section-card">', unsafe_allow_html=True)

uploaded_file = st.file_uploader(
    "ТЗ или спецификация (.docx, .xlsx, .pdf)",
    type=["docx", "xlsx", "pdf"],
    accept_multiple_files=False,
)
st.caption("Распознавание достаёт наименование/ед.изм/кол-во/цену из документа и добавит их "
           "в позиции текущего лота. Валюта, пошлина, кол-во машин, цена продажи, "
           "доп.расходы — это ваши бизнес-решения, документ их не содержит, заполните "
           "их вручную в таблице ниже.")

recognize_btn = st.button("Распознать", type="primary", disabled=uploaded_file is None)

if uploaded_file and recognize_btn:
    tmp_path = save_uploaded_file(uploaded_file)
    try:
        with st.spinner("Читаю документ..."):
            raw_text = extract_any(tmp_path)
            extracted_items = extract_items_free(tmp_path)
        st.session_state["raw_text"] = raw_text[:8000]
        if lot_type == "kz":
            st.session_state[items_state_key] = [
                normalize_item_kz({"name": it.get("name"), "qty": it.get("qty"),
                                    "purchase_price_ddp": it.get("unit_price")})
                for it in extracted_items
            ]
        else:
            st.session_state[items_state_key] = [
                normalize_item_fx({"name": it.get("name"), "unit": it.get("unit"),
                                    "qty": it.get("qty"), "price_fca": it.get("unit_price"),
                                    "duty_rate_pct": 5.0})
                for it in extracted_items
            ]
        st.session_state.pop(items_editor_key, None)
        st.session_state.pop(items_seed_key, None)
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
                st.session_state[items_state_key] = [
                    normalize_item_kz({"name": it.get("name"), "qty": it.get("qty"),
                                        "purchase_price_ddp": it.get("unit_price")})
                    for it in extracted_items
                ]
            else:
                st.session_state[items_state_key] = [
                    normalize_item_fx({"name": it.get("name"), "unit": it.get("unit"),
                                        "qty": it.get("qty"), "price_fca": it.get("unit_price"),
                                        "duty_rate_pct": 5.0})
                    for it in extracted_items
                ]
            st.session_state.pop(items_editor_key, None)
            st.session_state.pop(items_seed_key, None)
            st.session_state["generated_file"] = None
            st.success(f"LLM нашёл позиций: {len(extracted_items)}")
        except Exception as exc:
            st.error(f"Ошибка LLM: {exc}")

st.markdown("</div>", unsafe_allow_html=True)

# ------------------------------------------------------- Step 2: товары ----
st.divider()
items_heading_col, items_reset_col = st.columns([9, 1], vertical_alignment="center")
with items_heading_col:
    step_heading("04", f"Позиции лота {lot_ids.index(active_id) + 1}")
with items_reset_col:
    with st.container(key=f"icon_reset_items_{lot_type}_{active_id}"):
        st.button("", key=f"btn_reset_items_{lot_type}_{active_id}",
                  icon=":material/restart_alt:", on_click=reset_items,
                  help="Очистить таблицу позиций этого лота до одной пустой строки.")
st.caption("Чтобы удалить строку: выделите её слева (наведите на номер строки) "
           "и нажмите на значок корзины сверху таблицы, либо клавишу Delete — "
           "строка исчезнет сразу, без лишних шагов."
           + (" Страна происхождения / ТН ВЭД / транспорт указываются на каждый "
              "товар отдельно — они могут отличаться от позиции к позиции."
              if lot_type == "foreign" else ""))

DEFAULT_ROW_KZ = {"name": "", "qty": 1, "purchase_price_ddp": 0.0, "extra_cost": 0.0}
DEFAULT_ROW_FX = {"name": "", "unit": "", "qty": 1, "price_fca": 0.0, "sale_price_kzt": 0.0,
                   "duty_rate_pct": 5.0, "truck_count": 1, "overhead": 0.0, "extra_cost": 0.0,
                   "country": "", "tnved": "", "transport": ""}

if lot_type == "kz":
    # THE ACTUAL BUG (previous "add row" workaround didn't touch this): a
    # fresh pd.DataFrame was built from items_state_key and handed to
    # data_editor(key=...) on *every single rerun*, including the very
    # rerun that a keystroke inside the editor itself triggers. Streamlit
    # treats a freshly-built `data` argument as a new snapshot to layer the
    # user's pending edit on top of - round-tripping the value through
    # normalize_item_kz on every keystroke made that snapshot just different
    # enough, often enough, that the grid would revert the in-flight edit
    # and only keep it on the next identical attempt. Building the seed
    # dataframe once and never rebuilding it (Streamlit owns all further
    # state for this key) removes the feedback loop entirely - the editor
    # is the single source of truth for what's on screen; items_state_key
    # is only a read-only mirror kept in sync for validation/export below.
    if items_seed_key not in st.session_state:
        current_items = st.session_state[items_state_key] or [dict(DEFAULT_ROW_KZ)]
        st.session_state[items_seed_key] = pd.DataFrame(
            current_items, columns=["name", "qty", "purchase_price_ddp", "extra_cost"])
    # Streamlit's "small"/"medium"/"large" width categories are rough hints,
    # not sized to the label's actual text - a long header still truncates
    # inside a "medium" column. Explicit pixel widths (supported alongside
    # the categories) let each column fit its own header; anything that
    # doesn't fit on one line goes into a help= tooltip instead.
    edited_df = st.data_editor(
        st.session_state[items_seed_key], width="stretch", hide_index=True, num_rows="dynamic",
        column_config={
            "name": st.column_config.TextColumn("Наименование", width=280),
            "qty": st.column_config.NumberColumn("Кол-во", min_value=1, step=1,
                                                  format="%d", width=90),
            "purchase_price_ddp": st.column_config.NumberColumn(
                "Цена DDP, тнг", help="Цена закупки DDP (с НДС), тенге.",
                min_value=0, step=100, format="%.2f", width=150),
            "extra_cost": st.column_config.NumberColumn(
                "Доп.расходы, тнг", help="Прочие расходы по товару, тенге.",
                min_value=0, step=1000, format="%.2f", width=150),
        },
        key=items_editor_key,
    )
    # Read-only mirror for validation/export (Generate button, currency
    # hint) - never fed back into the editor above, so it can't create the
    # feedback loop described up top.
    st.session_state[items_state_key] = [
        normalize_item_kz(row) for row in edited_df.fillna("").to_dict("records")
    ]
    items = [it for it in st.session_state[items_state_key] if it["name"].strip()]
else:
    cols = ["name", "unit", "qty", "price_fca", "sale_price_kzt", "duty_rate_pct",
            "truck_count", "overhead", "extra_cost", "country", "tnved", "transport"]
    if items_seed_key not in st.session_state:
        current_items = st.session_state[items_state_key] or [dict(DEFAULT_ROW_FX)]
        st.session_state[items_seed_key] = pd.DataFrame(current_items, columns=cols)
    currency_now = st.session_state.get(k("currency"), "USD")
    edited_df = st.data_editor(
        st.session_state[items_seed_key], width="stretch", hide_index=True, num_rows="dynamic",
        column_config={
            "name": st.column_config.TextColumn("Наименование", width=280),
            "unit": st.column_config.TextColumn("Ед.изм", width=80),
            "qty": st.column_config.NumberColumn("Кол-во", min_value=1, step=1,
                                                  format="%d", width=90),
            "price_fca": st.column_config.NumberColumn(
                f"Цена FCA, {currency_now}", help=f"Цена FCA за единицу, {currency_now}.",
                min_value=0, step=10, format="%.2f", width=140),
            "sale_price_kzt": st.column_config.NumberColumn(
                "Цена продажи, тнг", help="Цена без НДС, которую вы выставляете заказчику, тенге/шт.",
                min_value=0, step=1000, format="%.2f", width=160),
            "duty_rate_pct": st.column_config.NumberColumn(
                "Пошлина, %", min_value=0, max_value=100, step=0.5,
                format="%.1f", width=110),
            "truck_count": st.column_config.NumberColumn(
                "Кол-во машин", help="= кол-во деклараций ГТД (1 машина = 1 декларация).",
                min_value=1, step=1, format="%d", width=130),
            "overhead": st.column_config.NumberColumn(
                f"Накладные, {currency_now}", help="Нет единого стандарта — впишите свою сумму.",
                min_value=0, step=10, format="%.2f", width=150),
            "extra_cost": st.column_config.NumberColumn(
                f"Доп.расходы, {currency_now}", help="Прочие расходы по товару.",
                min_value=0, step=10, format="%.2f", width=150),
            "country": st.column_config.TextColumn("Страна происхождения", width=180),
            "tnved": st.column_config.TextColumn("ТН ВЭД", width=120),
            "transport": st.column_config.TextColumn(
                "Транспорт", help="Кол-во подвижного состава / вид транспорта.", width=150),
        },
        key=items_editor_key,
    )
    st.session_state[items_state_key] = [
        normalize_item_fx(row) for row in edited_df.fillna("").to_dict("records")
    ]
    items = [it for it in st.session_state[items_state_key] if it["name"].strip()]

# --------------------------------------------------- Step 3: данные лота ---
st.divider()
header_heading_col, header_reset_col = st.columns([9, 1], vertical_alignment="center")
with header_heading_col:
    step_heading("05", f"Данные лота {lot_ids.index(active_id) + 1}")
with header_reset_col:
    with st.container(key=f"icon_reset_header_{lot_type}_{active_id}"):
        st.button("", key=f"btn_reset_header_{lot_type}_{active_id}",
                  icon=":material/restart_alt:", on_click=reset_lot_header,
                  help="Сбросить менеджера, заказчика, даты, наценку, курс и "
                       "остальные поля этого лота до значений по умолчанию.")

left_col, right_col = st.columns(2)

with left_col:
    st.text_input("Менеджер", key=k("manager"), placeholder="Введите имя...")
    st.text_input("Номер лота", key=k("lot_number"), placeholder="Введите номер лота...")
    st.date_input("Дата расчёта", key=k("calc_date"), format="DD.MM.YYYY")

    if lot_type == "kz":
        st.number_input("Сумма дорожных расходов, тнг", key=k("road_cost"),
                         min_value=0.0, step=1000.0, format="%.2f")
    else:
        st.number_input(f"Дорога, всего по лоту, {st.session_state[k('currency')]}",
                         key=k("road_cost"), min_value=0.0, step=1000.0, format="%.2f")

with right_col:
    st.text_input("Заказчик", key=k("supplier"), placeholder="Введите заказчика...")
    if lot_type == "kz":
        st.number_input("Коэффициент наценки (> 1)", key=k("markup_coef"),
                         min_value=1.01, step=0.05, format="%.2f")
    else:
        st.number_input("Коэфф. наценки (DAP → Вход DAP, > 1)", key=k("markup_coef"),
                         min_value=1.01, step=0.05, format="%.2f")
        st.number_input("НДС на ввоз, %", key=k("vat_rate"),
                         min_value=0.0, max_value=100.0, step=0.5, format="%.1f")

    st.date_input("Начало лота", key=k("lot_start"), format="DD.MM.YYYY")
    st.date_input("Окончание лота", key=k("lot_end"), format="DD.MM.YYYY")

    st.number_input("Срок производства, дней", key=k("lead_time_days"),
                     min_value=1, step=1, format="%d")
    if lot_type == "foreign":
        st.number_input("Срок поставки, дней", key=k("delivery_days"),
                         min_value=1, step=1, format="%d")

# --- Курс валюты ---
def on_fetch_rate(currency: str, target_key: str) -> None:
    """Runs BEFORE the script reruns/re-instantiates widgets, so it's safe
    to write to st.session_state[target_key] here (unlike doing it after
    the number_input widget has already been created in the same run)."""
    try:
        rate = get_rate(currency)
        st.session_state[target_key] = float(rate)
        st.session_state["_rate_status"] = ("success", currency, float(rate))
    except Exception as exc:
        st.session_state["_rate_status"] = ("error", currency, str(exc))


if lot_type == "kz":
    rate_left, rate_right = st.columns([3.2, 1])
    with rate_left:
        st.number_input("Курс USD, тнг (для отчёта прибыли в $)", key=k("usd_rate"),
                         min_value=0.0, step=0.01, format="%.2f")
    with rate_right:
        st.markdown("<div style='height:1.75rem'></div>", unsafe_allow_html=True)
        st.button("с Нацбанка РК", width="stretch", key=f"btn_rate_{lot_type}_{active_id}",
                   on_click=on_fetch_rate, args=("USD", k("usd_rate")))
else:
    cur_left, rate_left, rate_right = st.columns([1.1, 2.1, 1])
    with cur_left:
        st.selectbox("Валюта закупки", ["USD", "RUB", "EUR"], key=k("currency"))
    with rate_left:
        st.number_input(f"Курс {st.session_state[k('currency')]}, тнг",
                         key=k("fx_rate"), min_value=0.0, step=0.01, format="%.2f")
    with rate_right:
        st.markdown("<div style='height:1.75rem'></div>", unsafe_allow_html=True)
        st.button("с Нацбанка РК", width="stretch", key=f"btn_rate_{lot_type}_{active_id}",
                   on_click=on_fetch_rate, args=(st.session_state[k("currency")], k("fx_rate")))
    countries_used = {it["country"].strip() for it in items if it.get("country")}
    suggested_currencies = {currency_for_country(c) for c in countries_used}
    if suggested_currencies and suggested_currencies != {st.session_state[k("currency")]}:
        hint = ", ".join(sorted(suggested_currencies))
        st.caption(f"По странам происхождения в позициях обычно используют: {hint} — "
                   f"при необходимости переключите валюту выше.")

# All header widgets for this lot have rendered by now - copy their current
# values into the durable store so they survive the next time this lot's
# widgets DON'T render (i.e. as soon as another lot becomes active).
for _field in lot_header_store[active_id]:
    lot_header_store[active_id][_field] = st.session_state[k(_field)]

_rate_status = st.session_state.pop("_rate_status", None)
if _rate_status:
    _kind, _cur, _payload = _rate_status
    if _kind == "success":
        st.toast(f"Курс {_cur}: {_payload:.2f} тнг.")
    else:
        st.error(f"Не удалось получить курс {_cur}: {_payload}")

# ------------------------------------------------------------ Generate -----
st.divider()

if st.button("Сформировать расчёт по всем лотам", type="primary", width="stretch"):
    template_path = TEMPLATE_PATHS[lot_type]
    lots = []
    errors = []

    for pos, lid in enumerate(lot_ids, start=1):
        # Read from lot_header_store, NOT st.session_state[f"lot_{lot_type}_{lid}_..."]
        # directly - only the *active* lot's widgets are instantiated this
        # run, and Streamlit discards a widget's value the moment it stops
        # being rendered (see the comment by lot_header_store's definition
        # above). Generate loops over every lot in the tender, so reading
        # the raw widget key would silently read stale/missing data for
        # every lot except whichever one happened to be on screen when the
        # button was clicked.
        fields = lot_header_store.get(lid, {})

        lot_items_raw = st.session_state.get(f"items_{lot_type}_{lid}", [])
        lot_items = [it for it in lot_items_raw if it["name"].strip()]
        if not lot_items:
            errors.append(f"Лот {pos}: добавьте хотя бы одну позицию с наименованием.")
            continue

        calc_date = fields.get("calc_date")
        if not calc_date:
            errors.append(f"Лот {pos}: укажите дату расчёта.")
            continue

        if lot_type == "kz":
            usd_rate = float(fields.get("usd_rate") or 0)
            if usd_rate <= 0:
                errors.append(f"Лот {pos}: укажите курс USD (тг.).")
                continue
            header = {
                "manager": fields.get("manager", "").strip(),
                "supplier": fields.get("supplier", "").strip(),
                "lot_number": fields.get("lot_number", "").strip(),
                "calc_date": fmt_date(calc_date),
                "lot_start": fmt_date(fields.get("lot_start")),
                "lot_end": fmt_date(fields.get("lot_end")),
                "lead_time_days": int(fields.get("lead_time_days", 10)),
                "markup_coef": float(fields.get("markup_coef", 1.5)),
                "usd_rate": usd_rate,
                "road_cost": float(fields.get("road_cost", 0)),
            }
        else:
            fx_rate = float(fields.get("fx_rate") or 0)
            currency = fields.get("currency", "USD")
            if fx_rate <= 0:
                errors.append(f"Лот {pos}: укажите курс {currency} (тг.).")
                continue
            # The road-cost split formula in the foreign template divides
            # each item's road price by the *lot's total* purchase sum
            # (=G12/$G$13*...) - if every item has price_fca=0, that total is
            # zero and Excel would show #DIV/0! for every item's road cost.
            purchase_sum = sum(it["price_fca"] * it["qty"] for it in lot_items)
            if purchase_sum <= 0:
                errors.append(f"Лот {pos}: укажите цену FCA хотя бы для одной позиции — "
                               f"иначе в Excel формула дороги поделит на нулевую сумму закупки.")
                continue
            header = {
                "manager": fields.get("manager", "").strip(),
                "supplier": fields.get("supplier", "").strip(),
                "lot_number": fields.get("lot_number", "").strip(),
                "calc_date": fmt_date(calc_date),
                "lot_start": fmt_date(fields.get("lot_start")),
                "lot_end": fmt_date(fields.get("lot_end")),
                "lead_time_days": int(fields.get("lead_time_days", 10)),
                "delivery_days": int(fields.get("delivery_days", 30)),
                "markup_coef": float(fields.get("markup_coef", 1.2)),
                "vat_rate": float(fields.get("vat_rate", 16.0)) / 100,
                "road_cost": float(fields.get("road_cost", 0)),
                "currency": currency,
                "usd_rate": fx_rate,
            }
            lot_items = [{**it, "duty_rate": it["duty_rate_pct"] / 100} for it in lot_items]

        lots.append({"header": header, "items": lot_items})

    if errors:
        st.error("\n\n".join(errors))
    elif not os.path.exists(template_path):
        st.error(f"Шаблон {template_path} не найден.")
    else:
        try:
            with st.spinner("Формирую Excel..."):
                out_path = tempfile.mktemp(suffix=".xlsx")
                if lot_type == "kz":
                    fill_lots_kz(template_path, out_path, lots)
                else:
                    fill_lots_foreign(template_path, out_path, lots)

                with open(out_path, "rb") as f:
                    st.session_state["generated_file"] = f.read()
                os.unlink(out_path)
            st.session_state["generated_name"] = f"расчёт_{len(lots)}_лотов.xlsx"
            st.success(f"Готово, лотов: {len(lots)}. Скачайте файл ниже.")
        except Exception as exc:
            st.error(f"Ошибка при формировании: {exc}")

if st.session_state.get("generated_file"):
    st.download_button(
        "Скачать Excel", data=st.session_state["generated_file"],
        file_name=st.session_state["generated_name"],
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        type="primary", width="stretch",
    )
