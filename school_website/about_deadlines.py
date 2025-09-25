from typing import Any
import os
import requests
from bs4 import BeautifulSoup


def get_deadlines() -> list[tuple[str, Any, Any]]:
    with requests.Session() as s:
        # Авторизация
        login_payload = {
            "email": "почта",     # замени на os.getenv("API_ACCOUNT_EMAIL")
            "password": "пароль"  # замени на os.getenv("API_ACCOUNT_PASSWORD")
        }

        login_response = s.post(
            f"https://{os.getenv('API_DOMAIN')}/login",
            data=login_payload
        )
        if login_response.status_code != 200:
            raise RuntimeError(f"Ошибка логина: {login_response.status_code}")

        # Загружаем страницу с уроками
        live_url = (
            f"https://{os.getenv('API_DOMAIN')}/student_live/index"
            f"?course_id={os.getenv('COURSE_ID') or '1856'}"
        )
        live_response = s.get(live_url)
        if live_response.status_code != 200:
            raise RuntimeError(
                f"Ошибка доступа к student_live: {live_response.status_code}"
            )

        # Парсим HTML
        soup = BeautifulSoup(live_response.text, "html.parser")
        deadlines = []

        # Пробуем найти таблицу
        for row in soup.select("table tr"):
            cols = row.find_all("td")
            if len(cols) < 3:
                continue

            lesson_id = cols[0].get_text(strip=True)
            title = cols[1].get_text(strip=True)
            deadline = cols[-1].get_text(strip=True).split()[0]  # обычно в последней колонке

            if deadline:  # пропускаем пустые строки
                deadlines.append((lesson_id, title, deadline))

        return deadlines
for d in get_deadlines():
    print(d)
