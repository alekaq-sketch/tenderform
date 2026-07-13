# Heat Energy Tender Calculator

Streamlit-приложение для подготовки тендерных расчетов: загружает ТЗ/спецификацию, извлекает позиции, позволяет проверить данные в браузере и скачать готовый Excel по шаблону.

## Что умеет

- Загружает `.docx`, `.xlsx`, `.pdf`.
- Извлекает позиции бесплатно через эвристики.
- Опционально уточняет распознавание через Claude API.
- Получает курс USD/KZT с открытого API Нацбанка РК.
- Заполняет Excel-шаблон `template.xlsx` и сохраняет формулы.
- Работает локально и на Streamlit Community Cloud.

## Быстрый запуск локально

```bash
pip install -r requirements.txt
streamlit run app.py
```

После запуска приложение откроется на `http://localhost:8501`.

## Деплой на Streamlit Community Cloud

1. Создайте репозиторий на GitHub и запушьте этот проект.
2. Откройте `https://share.streamlit.io`.
3. Нажмите `Create app`.
4. Выберите ваш GitHub-репозиторий.
5. Укажите branch `main` и main file path `app.py`.
6. В `Advanced settings` при необходимости выберите Python `3.12`.
7. Нажмите `Deploy`.

Для базового режима секреты не нужны. Если хотите включить Claude-распознавание без ручного ввода ключа, добавьте secret в настройках приложения:

```toml
ANTHROPIC_API_KEY = "sk-ant-..."
```

Локальный пример лежит в `.streamlit/secrets.toml.example`. Настоящий `.streamlit/secrets.toml` не коммитьте.

## Подготовка к GitHub

Если репозиторий еще не создан локально:

```bash
git init
git add .
git commit -m "Prepare Streamlit tender calculator"
git branch -M main
git remote add origin https://github.com/USERNAME/REPOSITORY.git
git push -u origin main
```

Если git уже настроен:

```bash
git add .
git commit -m "Prepare Streamlit tender calculator"
git push
```

## Структура проекта

```text
app.py                       Streamlit-интерфейс
extract_raw.py               Извлечение текста и таблиц из документов
extract_heuristic.py         Бесплатное распознавание позиций по таблицам
extract_with_llm.py          Опциональное распознавание через Claude
fetch_usd_rate.py            Получение курса USD/KZT
fill_tender_template.py      Заполнение Excel-шаблона
template.xlsx                Шаблон расчета
requirements.txt             Python-зависимости для деплоя
.streamlit/config.toml       Настройки Streamlit
.streamlit/secrets.toml.example Пример локальных секретов
```

## Важно

- `template.xlsx` нужен приложению, не удаляйте его из репозитория.
- `.streamlit/secrets.toml` должен оставаться локальным и уже добавлен в `.gitignore`.
- Папки `__pycache__`, `venv`, временные файлы и локальные выгрузки не должны попадать в git.
