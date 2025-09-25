from typing import Any
import os
import requests
from bs4 import BeautifulSoup  # если надо будет парсить HTML


def get_deadlines() -> list[tuple[str, Any, Any]]:
    with requests.Session() as s:
        # Логинимся через POST /login
        login_payload = {
            "email": "почта",     # замени на os.getenv("API_ACCOUNT_EMAIL")
            "password": "пароль"  # замени на os.getenv("API_ACCOUNT_PASSWORD")
        }

        login_response = s.post(
            f"https://{os.getenv('API_DOMAIN')}/login",
            data=login_payload  # <--- важно: здесь data, а не json
        )

        if login_response.status_code != 200:
            raise RuntimeError(f"Ошибка логина: {login_response.status_code} {login_response.text}")

        # Теперь сессия залогинена (cookie внутри s)
        # Дёргаем страницу с уроками/дз
        lessons_response = s.get(
            f"https://{os.getenv('API_DOMAIN')}/student_homework/index"
        )

        if lessons_response.status_code != 200:
            raise RuntimeError(f"Ошибка получения данных: {lessons_response.status_code} {lessons_response.text}")

        # Тут скорее всего HTML, а не JSON
        html = lessons_response.text
        soup = BeautifulSoup(html, "html.parser")

        deadlines = []
        # Нужно посмотреть, как именно устроена таблица на /student_homework/index
        # Допустим, там <tr><td>ID</td><td>Название</td><td>Дедлайн</td></tr>
        for row in soup.select("table tr"):
            cols = row.find_all("td")
            if len(cols) < 3:
                continue
            lesson_id = cols[0].get_text(strip=True)
            title = cols[1].get_text(strip=True)
            deadline = cols[2].get_text(strip=True).split()[0]
            deadlines.append((lesson_id, title, deadline))

        return deadlines
