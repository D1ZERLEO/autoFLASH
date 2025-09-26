from typing import Any
import os
import requests
from bs4 import BeautifulSoup
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

def get_deadlines() -> list[tuple[str, Any, Any]]:
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
    resp = session.get("https://admin.100points.ru/student_live/index",
                       params={"subject_id": "20", "course_id": "1856"})
    soup = BeautifulSoup(resp.text, "html.parser")

    deadlines = []

    # Находим все заголовки уроков
    lesson_headers = soup.select("thead th[data-lesson-id]")
    for header in lesson_headers:
        lesson_id = header.get("data-lesson-id")
        title = header.get_text(strip=True)

        # Ищем все элементы дедлайнов по этому уроку
        deadline_elems = soup.find_all("b", id=lambda x: x and x.startswith(f"deadline_{lesson_id}"))

        if not deadline_elems:
            continue  # если дедлайна нет → пропускаем

        # Берём первую дату (или можно выбрать минимальную)
        dt_raw = deadline_elems[0].get("data-datetime")
        try:
            date_obj = datetime.strptime(dt_raw, "%Y-%m-%dT%H:%M")
            formatted_date = date_obj.strftime("%d.%m.%Y")
            deadlines.append((lesson_id, title, formatted_date))
        except Exception:
            logger.warning(f"Не удалось распарсить дату: {dt_raw}")

    return deadlines
