from typing import Any
import os
import requests


def get_deadlines() -> list[tuple[str, Any, Any]]:
    with requests.Session() as s:
        # Авторизация по почте и паролю
        login_payload = {
            "email": os.getenv("API_ACCOUNT_EMAIL"),   # <-- замени на os.getenv("API_ACCOUNT_EMAIL")
            "password": os.getenv("API_ACCOUNT_PASSWORD")  # <-- замени на os.getenv("API_ACCOUNT_PASSWORD")
        }

        login_response = s.post(
            f"https://{os.getenv('API_DOMAIN')}/api/auth/login",
            json=login_payload
        ).json()

        if login_response.get("status") != "success":
            raise RuntimeError(f"Ошибка авторизации: {login_response}")

        # Теперь пробуем запросить уроки
        lessons_response = s.post(
            f"https://{os.getenv('API_DOMAIN')}/api/student/courses/1856/lessons"
        ).json()

        if "lessons" not in lessons_response:
            raise RuntimeError(f"Ошибка доступа к курсу: {lessons_response}")

    deadlines = []
    for lesson in lessons_response["lessons"]:
        if lesson["deadline"] is None:
            continue
        deadlines.append(
            (str(lesson["id"]), lesson["title"], lesson["deadline"].split()[0])
        )

    return deadlines
