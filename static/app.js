const $ = (id) => document.getElementById(id);

let items = [];
const dateFields = ["f_calc_date", "f_lot_start", "f_lot_end"];

function todayStr() {
  const d = new Date();
  const p = (n) => String(n).padStart(2, "0");
  return `${p(d.getDate())}.${p(d.getMonth() + 1)}.${d.getFullYear()}`;
}

function formatDateInputValue(value) {
  const digits = String(value ?? "").replace(/\D/g, "").slice(0, 8);
  if (digits.length <= 2) return digits;
  if (digits.length <= 4) return `${digits.slice(0, 2)}.${digits.slice(2)}`;
  return `${digits.slice(0, 2)}.${digits.slice(2, 4)}.${digits.slice(4)}`;
}

function applyDateFormatting(input) {
  input.value = formatDateInputValue(input.value);
}

function bindDateField(id) {
  const el = $(id);
  el.addEventListener("input", () => applyDateFormatting(el));
  if (!el.value) {
    el.value = id === "f_calc_date" ? todayStr() : "";
    applyDateFormatting(el);
  }
}

function updateStamp() {
  $("stampLot").textContent = $("f_lot_number").value || "—";
  $("stampDate").textContent = $("f_calc_date").value || todayStr();
}

dateFields.forEach(bindDateField);
["f_lot_number", "f_calc_date"].forEach((id) => $(id).addEventListener("input", updateStamp));
updateStamp();

/* ---------- Загрузка файла ---------- */
const dropzone = $("dropzone");
const fileInput = $("fileInput");
const templateFileInput = $("templateFileInput");

templateFileInput.addEventListener("change", () => {
  const file = templateFileInput.files[0];
  if (file) {
    setStatus("genStatus", `Шаблон выбран: ${file.name}`, "ok");
  }
});

["dragover", "dragenter"].forEach((ev) =>
  dropzone.addEventListener(ev, (e) => { e.preventDefault(); dropzone.classList.add("dragover"); })
);
["dragleave", "drop"].forEach((ev) =>
  dropzone.addEventListener(ev, (e) => { e.preventDefault(); dropzone.classList.remove("dragover"); })
);
dropzone.addEventListener("drop", (e) => {
  const f = e.dataTransfer.files[0];
  if (f) { fileInput.files = e.dataTransfer.files; handleFile(f); }
});
fileInput.addEventListener("change", () => {
  if (fileInput.files[0]) handleFile(fileInput.files[0]);
});

async function handleFile(file) {
  $("dropzoneFile").textContent = file.name;
  setStatus("uploadStatus", "Читаю документ…", "loading");
  $("llmRow").hidden = true;

  const form = new FormData();
  form.append("file", file);

  try {
    const res = await fetch("/api/upload", { method: "POST", body: form });
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || "Ошибка загрузки");

    $("rawText").textContent = data.raw_text || "(пусто)";
    $("rawTextBox").hidden = false;
    $("llmRow").hidden = false;

    if (data.items && data.items.length) {
      items = data.items.map(normalizeItem);
      renderItems();
      setStatus("uploadStatus", `Найдено позиций: ${items.length}. Проверьте таблицу ниже.`, "ok");
    } else {
      setStatus("uploadStatus", "Не нашёл таблицу позиций по ключевым словам — попробуйте LLM-распознавание ниже или заполните таблицу вручную.", "err");
    }
  } catch (e) {
    setStatus("uploadStatus", e.message, "err");
  }
}

function normalizeItem(i) {
  return {
    name: i.name || "",
    unit: i.unit || "",
    qty: i.qty ?? "",
    unit_price: i.unit_price ?? "",
  };
}

/* ---------- LLM-распознавание (опционально) ---------- */
$("llmBtn").addEventListener("click", async () => {
  const apiKey = $("apiKey").value.trim();
  if (!apiKey) { setStatus("uploadStatus", "Введите API-ключ, чтобы использовать LLM.", "err"); return; }

  setStatus("uploadStatus", "Извлекаю данные через Claude…", "loading");
  try {
    const res = await fetch("/api/llm-extract", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ raw_text: $("rawText").textContent, api_key: apiKey }),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || "Ошибка LLM");

    items = (data.items || []).map(normalizeItem);
    renderItems();
    setStatus("uploadStatus", `Найдено позиций: ${items.length}. Проверьте таблицу ниже перед расчётом.`, "ok");
  } catch (e) {
    setStatus("uploadStatus", e.message, "err");
  }
});

/* ---------- Таблица позиций ---------- */
function renderItems() {
  const body = $("itemsBody");
  body.innerHTML = "";
  items.forEach((item, idx) => {
    const tr = document.createElement("tr");
    tr.innerHTML = `
      <td><input type="text" data-field="name" value="${escapeAttr(item.name)}" placeholder="Наименование"></td>
      <td><input type="text" data-field="unit" value="${escapeAttr(item.unit)}" placeholder="ед."></td>
      <td class="col-num"><input type="number" data-field="qty" value="${item.qty}" placeholder="0"></td>
      <td class="col-num" style="display:flex;gap:4px;align-items:center;"><span style="font-size:13px;font-weight:600;color:#999;">₸</span><input type="number" data-field="unit_price" value="${item.unit_price}" placeholder="0" style="flex:1;"></td>
      <td class="col-del"><button class="row-del" title="Удалить строку">✕</button></td>
    `;
    tr.querySelectorAll("input").forEach((inp) => {
      inp.addEventListener("input", () => { items[idx][inp.dataset.field] = inp.value; });
    });
    tr.querySelector(".row-del").addEventListener("click", () => {
      items.splice(idx, 1);
      renderItems();
    });
    body.appendChild(tr);
  });
}
function escapeAttr(s) { return String(s ?? "").replace(/"/g, "&quot;"); }

$("addRowBtn").addEventListener("click", () => {
  items.push({ name: "", unit: "", qty: "", unit_price: "" });
  renderItems();
});
renderItems();

/* ---------- Курс USD ---------- */
$("usdBtn").addEventListener("click", async () => {
  $("usdBtn").disabled = true;
  $("usdBtn").textContent = "…";
  try {
    const res = await fetch("/api/usd-rate");
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || "Не удалось получить курс");
    $("f_usd_rate").value = data.rate;
  } catch (e) {
    setStatus("genStatus", e.message, "err");
  } finally {
    $("usdBtn").disabled = false;
    $("usdBtn").textContent = "с Нацбанка РК";
  }
});

function composeItemName(item) {
  return item.name || "";
}

async function generateOfflineWorkbook(header, payloadItems) {
  if (!window.XLSX) throw new Error("Библиотека Excel недоступна для офлайн-режима.");
  const templateFile = templateFileInput.files[0];
  if (!templateFile) throw new Error("Выберите файл шаблона Excel для офлайн-режима.");

  const data = await templateFile.arrayBuffer();
  const workbook = XLSX.read(data, { type: "array" });
  const ws = workbook.Sheets["расчет"] || workbook.Sheets[workbook.SheetNames[0]];
  if (!ws) throw new Error("В шаблоне не найден лист 'расчет'.");

  ws["B2"] = header.manager || "";
  ws["B3"] = header.supplier || "";
  ws["R2"] = header.lot_number ? `лот ${header.lot_number}` : "";
  ws["B4"] = header.calc_date ? `Дата:${header.calc_date}` : "";
  ws["B5"] = header.lot_start ? `Дата начала лота:${header.lot_start}` : "";
  ws["B6"] = header.lot_end ? `Дата окончания лота: ${header.lot_end}` : "";
  ws["B7"] = header.lead_time_days ? `Срок производства: ${header.lead_time_days} дн` : "";
  ws["J9"] = header.markup_coef || 1;
  ws["K9"] = header.usd_rate || 0;
  ws["H18"] = Number(header.road_cost) || 0;

  const firstRow = 12;
  const columns = ["A", "B", "C", "D", "E", "F", "G", "H", "I", "J", "K", "L", "M", "N", "O", "P", "Q", "R", "S"];
  for (let rowIndex = 0; rowIndex < payloadItems.length; rowIndex += 1) {
    const row = firstRow + rowIndex;
    if (rowIndex > 0) {
      for (const col of columns) {
        const srcCell = ws[`${col}${firstRow}`];
        if (!srcCell) continue;
        const value = srcCell.v;
        if (typeof value === "string" && value.startsWith("=")) {
          ws[`${col}${row}`] = { t: "s", v: value.replace(/12/g, String(row)) };
        } else {
          ws[`${col}${row}`] = value;
        }
      }
    }
    ws[`B${row}`] = rowIndex + 1;
    ws[`C${row}`] = payloadItems[rowIndex].item_name || "";
    ws[`D${row}`] = payloadItems[rowIndex].qty || 0;
    ws[`E${row}`] = payloadItems[rowIndex].purchase_price_ddp || 0;
  }

  const outBuffer = XLSX.write(workbook, { bookType: "xlsx", type: "array" });
  const blob = new Blob([outBuffer], { type: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `расчёт_${header.lot_number || "лот"}.xlsx`;
  a.click();
  URL.revokeObjectURL(url);
}

/* ---------- Формирование расчёта ---------- */
$("generateBtn").addEventListener("click", async () => {
  const header = {
    manager: $("f_manager").value,
    supplier: $("f_supplier").value,
    lot_number: $("f_lot_number").value,
    calc_date: $("f_calc_date").value || todayStr(),
    lot_start: $("f_lot_start").value,
    lot_end: $("f_lot_end").value,
    lead_time_days: Number($("f_lead_time_days").value) || 0,
    markup_coef: Number($("f_markup_coef").value) || 1,
    usd_rate: Number($("f_usd_rate").value) || 0,
    road_cost: Number($("f_road_cost").value) || 0,
  };
  const payloadItems = items
    .filter((i) => i.name && i.name.trim())
    .map((i) => ({
      item_name: composeItemName(i),
      qty: Number(i.qty) || 0,
      purchase_price_ddp: Number(i.unit_price) || 0,
    }));

  if (!payloadItems.length) { setStatus("genStatus", "Добавьте хотя бы одну позицию.", "err"); return; }
  if (!header.usd_rate) { setStatus("genStatus", "Укажите курс USD.", "err"); return; }

  const btn = $("generateBtn");
  btn.disabled = true;
  setStatus("genStatus", "Формирую файл…", "loading");

  try {
    const res = await fetch("/api/generate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ header, items: payloadItems }),
    });
    if (!res.ok) {
      const data = await res.json();
      throw new Error(data.error || "Ошибка формирования файла");
    }
    const blob = await res.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `расчёт_${header.lot_number || "лот"}.xlsx`;
    a.click();
    URL.revokeObjectURL(url);
    setStatus("genStatus", "Готово — файл скачан. Формулы пересчитаются при открытии в Excel.", "ok");
  } catch (serverError) {
    try {
      await generateOfflineWorkbook(header, payloadItems);
      setStatus("genStatus", "Готово — файл скачан офлайн. Дорожные расходы учтены.", "ok");
    } catch (offlineError) {
      setStatus("genStatus", offlineError.message || "Ошибка формирования файла", "err");
    }
  } finally {
    btn.disabled = false;
  }
});

function setStatus(id, text, kind) {
  const el = $(id);
  el.textContent = text;
  el.className = "status " + (kind || "");
}
