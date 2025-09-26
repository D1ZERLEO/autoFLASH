from typing import List, Tuple
import os
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta, timezone
from collections import Counter
import logging

logger = logging.getLogger(__name__)

def get_deadlines(s: requests.Session) -> List[Tuple[str, str, str]]:
    """
    Получаем дедлайны всех уроков через переданную сессию.
    Логин выполняется один раз здесь.
    """
    email = os.getenv('API_ACCOUNT_EMAIL')
    password = os.getenv('API_ACCOUNT_PASSWORD')
    domain = os.getenv('API_DOMAIN')

    if not email or not password or not domain:
        logger.error("Не заданы переменные окружения API_ACCOUNT_EMAIL / API_ACCOUNT_PASSWORD / API_DOMAIN")
        return []

    # Шаг 1: GET /login
    login_page = s.get(f"https://{domain}/login")
    soup = BeautifulSoup(login_page.text, "html.parser")
    csrf_meta = soup.find("meta", {"name": "csrf-token"})
    if not csrf_meta:
        logger.error("Не удалось найти CSRF токен на странице логина")
        return []
    csrf_token = csrf_meta.get("content")
    print("CSRF token:", csrf_token)

    # Шаг 2: POST /login
    headers = {
        "X-CSRF-TOKEN": csrf_token,
        "X-Requested-With": "XMLHttpRequest",
        "Referer": f"https://{domain}/login",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
    }
    login_data = {"email": email, "password": password, "_token": csrf_token}
    login_resp = s.post(f"https://{domain}/login", data=login_data, headers=headers)
    if "login" in login_resp.url or login_resp.status_code != 200:
        logger.error("Ошибка авторизации")
        return []

    # Шаг 3: GET страницы с уроками
    resp = s.get(f"https://{domain}/student_live/index", params={"subject_id": "20", "course_id": "1856"})
    soup = BeautifulSoup(resp.text, "html.parser")

    deadlines = []

    # Находим первую строку с th[data-lesson-id]
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
    tolerance = timedelta(minutes=30)

    for header in lesson_headers:
        lesson_id = header.get("data-lesson-id")
        title = header.get_text(strip=True)
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
            if abs(dt - now) <= tolerance:
                continue
            dates.append(dt.date())

        if not dates:
            continue

        # Берём самую популярную дату
        counter = Counter(dates)
        max_count = max(counter.values())
        candidates = [d for d, c in counter.items() if c == max_count]
        chosen_date = min(candidates)
        formatted_date = chosen_date.strftime("%d.%m.%Y")
        deadlines.append((lesson_id, title, formatted_date))

    return deadlines
