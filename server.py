"""
Локальный веб-сервер тендер-калькулятора.

Запуск:
    pip install -r requirements.txt
    python server.py
Открыть в браузере: http://localhost:5000
"""
import os
import tempfile
import traceback

from flask import Flask, request, jsonify, send_file, send_from_directory

from extract_raw import extract_any
from extract_heuristic import extract_items as extract_items_free
from extract_with_llm import extract_fields as extract_items_llm
from fetch_usd_rate import get_usd_rate
from fill_tender_template import fill_multi

app = Flask(__name__, static_folder="static", static_url_path="")
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TEMPLATE_PATH = os.path.join(BASE_DIR, "template.xlsx")


@app.route("/")
def index():
    return send_from_directory(app.static_folder, "index.html")


@app.route("/api/upload", methods=["POST"])
def api_upload():
    f = request.files.get("file")
    if not f:
        return jsonify({"error": "Файл не получен"}), 400

    suffix = os.path.splitext(f.filename)[1].lower()
    if suffix not in (".docx", ".xlsx", ".pdf"):
        return jsonify({"error": f"Формат {suffix} не поддерживается"}), 400

    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        f.save(tmp.name)
        tmp_path = tmp.name

    try:
        raw_text = extract_any(tmp_path)
        items = extract_items_free(tmp_path)
        return jsonify({"raw_text": raw_text[:8000], "items": items})
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500
    finally:
        os.unlink(tmp_path)


@app.route("/api/llm-extract", methods=["POST"])
def api_llm_extract():
    data = request.get_json(force=True)
    raw_text = data.get("raw_text", "")
    api_key = data.get("api_key", "")
    if not api_key:
        return jsonify({"error": "Нужен API-ключ"}), 400
    try:
        result = extract_items_llm(raw_text, api_key=api_key)
        return jsonify(result)
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


@app.route("/api/usd-rate")
def api_usd_rate():
    try:
        return jsonify({"rate": get_usd_rate()})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/generate", methods=["POST"])
def api_generate():
    data = request.get_json(force=True)
    header = data.get("header", {})
    items = data.get("items", [])
    if not items:
        return jsonify({"error": "Нет ни одной позиции"}), 400

    out_path = tempfile.mktemp(suffix=".xlsx")
    try:
        fill_multi(TEMPLATE_PATH, out_path, header, items)
        lot = header.get("lot_number") or "лот"
        return send_file(out_path, as_attachment=True,
                          download_name=f"расчёт_{lot}.xlsx")
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    print("Открой в браузере: http://localhost:5000")
    app.run(debug=True, port=5000)
