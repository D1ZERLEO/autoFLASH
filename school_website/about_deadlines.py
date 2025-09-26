from typing import Any, List, Tuple
import os
import requests
from bs4 import BeautifulSoup
import logging
from datetime import datetime, timedelta, timezone
from collections import Counter

logger = logging.getLogger(__name__)


def get_deadlines() -> List[Tuple[str, Any, Any]]:
    email = os.getenv('API_ACCOUNT_EMAIL')
    password = os.getenv('API_ACCOUNT_PASSWORD')

    if not email or not password:
        logger.error("Не заданы переменные окружения API_ACCOUNT_EMAIL и/или API_ACCOUNT_PASSWORD")
        return []

    session = requests.Session()

    # Логин
    login_page = session.get("https://admin.100points.ru/login")
    soup = BeautifulSoup(login_page.text, "html.parser")
    csrf_token = soup.find("input", {"name": "_token"}).get("value")

    login_data = {"email": email, "password": password, "_token": csrf_token}
    login_response = session.post("https://admin.100points.ru/login", data=login_data)

    if "login" in login_response.url:
        logger.error("Ошибка авторизации")
        return []

    # Загружаем страницу с уроками
    resp = session.get(
        "https://admin.100points.ru/student_live/index",
        params={"subject_id": "20", "course_id": "1856"}
    )
    soup = BeautifulSoup(resp.text, "html.parser")

    deadlines = []

    # Берём первую строку с th[data-lesson-id]
    top_row = None
    for tr in soup.find_all("tr"):
        ths = tr.find_all("th", attrs={"data-lesson-id": True})
        if ths:
            top_row = tr
            break

    if not top_row:
        logger.error("Не найден заголовок с th[data-lesson-id]")
        return []

    lesson_headers = top_row.find_all("th", attrs={"data-lesson-id": True})

    moscow_tz = timezone(timedelta(hours=3))
    now = datetime.now(moscow_tz)
    print(now)
    tolerance = timedelta(minutes=30)  # допуск ±30 минут

    for header in lesson_headers:
        lesson_id = header.get("data-lesson-id")
        title = header.get_text(strip=True)

        # Собираем все дедлайны по этому уроку
        deadline_elems = soup.find_all("b", id=lambda x: x and x.startswith(f"deadline_{lesson_id}"))

        if not deadline_elems:
            continue

        dates = []
        for elem in deadline_elems:
            dt_raw = elem.get("data-datetime")
            if not dt_raw:
                continue
            try:
                dt = datetime.fromisoformat(dt_raw)
            except ValueError:
                try:
                    dt = datetime.strptime(dt_raw, "%Y-%m-%dT%H:%M")
                except Exception:
                    logger.warning(f"Не удалось распарсить дату: {dt_raw}")
                    continue
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=moscow_tz)
            # Пропускаем "фейковые" дедлайны ≈ сейчас
            if abs(dt - now) <= tolerance:
                continue
        
            dates.append(dt.date())

        if not dates:
            continue

        # Находим самую популярную дату (mode)
        counter = Counter(dates)
        max_count = max(counter.values())
        candidates = [d for d, c in counter.items() if c == max_count]
        chosen_date = min(candidates)  # из популярных берём ближайшую по времени

        formatted_date = chosen_date.strftime("%d.%m.%Y")
        deadlines.append((lesson_id, title, formatted_date))

    print(deadlines)
    return deadlines
