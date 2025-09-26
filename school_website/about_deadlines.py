from typing import Any, List, Tuple
import os
import requests
from bs4 import BeautifulSoup
import logging
from datetime import datetime
from collections import Counter

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


def get_deadlines(course_id: str = "1856", subject_id: str = "20") -> List[Tuple[str, Any, Any]]:
    domain = os.getenv("API_DOMAIN")
    email = os.getenv("API_ACCOUNT_EMAIL")
    password = os.getenv("API_ACCOUNT_PASSWORD")

    if not domain or not email or not password:
        logger.error("Не заданы API_DOMAIN / API_ACCOUNT_EMAIL / API_ACCOUNT_PASSWORD")
        return []

    session = requests.Session()

    # 1) Получаем страницу логина и CSRF-токен
    login_url = f"https://{domain}/login"
    r = session.get(login_url, timeout=15)
    if r.status_code != 200:
        logger.error("Не удалось загрузить страницу логина: %s", r.status_code)
        return []

    soup = BeautifulSoup(r.text, "html.parser")
    token_input = soup.find("input", {"name": "_token"})
    if not token_input or not token_input.get("value"):
        logger.error("CSRF-токен не найден на странице логина (структура страницы изменилась).")
        return []
    csrf = token_input.get("value")

    # 2) Логинимся (форма обычная, data=)
    login_data = {"email": email, "password": password, "_token": csrf}
    login_resp = session.post(login_url, data=login_data, allow_redirects=True, timeout=15)

    # простая проверка успешности: пробуем получить страницу журнала и убедиться, что там есть thead
    live_url = f"https://{domain}/student_live/index"
    params = {"course_id": course_id, "subject_id": subject_id}
    page = session.get(live_url, params=params, timeout=15)
    if page.status_code != 200:
        logger.error("Не удалось загрузить student_live (status=%s).", page.status_code)
        return []

    soup = BeautifulSoup(page.text, "html.parser")

    
    

    # Найдём первую строку тр в thead, содержащую th с data-lesson-id
    top_row = None
    for tr in thead.find_all("tr"):
        ths = tr.find_all("th", attrs={"data-lesson-id": True})
        if ths:
            top_row = tr
            break

    if not top_row:
        logger.error("Не найден top-level row с th[data-lesson-id].")
        return []

    lesson_ths = top_row.find_all("th", attrs={"data-lesson-id": True})
    logger.info("Найдено уроков в верхней строке заголовка: %d", len(lesson_ths))

    deadlines = []

    for th in lesson_ths:
        lesson_id = th.get("data-lesson-id", "").strip()
        title = " ".join(th.stripped_strings)  # аккуратно берём весь текст заголовка
        if not lesson_id:
            continue

        # Найдём во всём документе все <b id="deadline_{lesson_id}user_id..."> и соберём data-datetime
        b_elems = soup.find_all("b", id=lambda x: x and x.startswith(f"deadline_{lesson_id}"))
        date_iso_list = []
        for b in b_elems:
            dt_raw = (b.get("data-datetime") or "").strip()
            if not dt_raw:
                continue
            # ожидаемый формат: 2025-10-02T23:59 (ISO-ish). Попробуем robust-парсинг:
            try:
                dt = datetime.fromisoformat(dt_raw)
            except Exception:
                try:
                    dt = datetime.strptime(dt_raw, "%Y-%m-%dT%H:%M")
                except Exception:
                    logger.debug("Не удалось распарсить data-datetime: %s (lesson %s)", dt_raw, lesson_id)
                    continue
            date_iso_list.append(dt.date().isoformat())  # YYYY-MM-DD

        if not date_iso_list:
            # ВАЖНО: если для урока нет ни одной валидной data-datetime — мы НЕ присваиваем "сегодня".
            logger.debug("Урок %s (%s) — дедлайнов не найдено, пропускаем.", lesson_id, title)
            continue
        # Берём наиболее частую дату (mode). При ничьей — выбираем раннюю дату среди кандидатов.
        counter = Counter(date_iso_list)
        max_count = max(counter.values())
        candidates = [d for d, c in counter.items() if c == max_count]
        chosen_iso = min(candidates)  # earliest among most-frequent
        chosen_date_obj = datetime.fromisoformat(chosen_iso).date()
        formatted = chosen_date_obj.strftime("%d.%m.%Y")

        deadlines.append((lesson_id, title, formatted))
        logger.info("Добавлен дедлайн: %s — %s — %s (count=%d)", lesson_id, title, formatted, max_count)

    logger.info("Всего дедлайнов собрано: %d", len(deadlines))

    # Опционально: отсортировать по дате (ранее -> позже)
    def _date_key(item):
        try:
            return datetime.strptime(item[2], "%d.%m.%Y").date()
        except Exception:
            return datetime.max.date()

    deadlines.sort(key=_date_key)
    print(deadlines)
    return deadlines
