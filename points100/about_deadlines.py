from typing import Any
import os

import requests

payload = {
    'email': os.getenv('STUDENT_ACCOUNT_EMAIL'),
    'password': os.getenv('STUDENT_ACCOUNT_PASSWORD')
}


def get_deadlines() -> list[tuple[str, Any, Any]]:
    # Запускаем сессию
    with requests.Session() as s:
        # Заголовки для запроса уроков
        headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json',
            'Authorization': 'Bearer 1938977|1wyh786iIQb7ehAe2rgT08HVPkOO5cHqPMPU6WAD'
            # Используем токен из заголовков, если он там есть
        }

        # Делаем POST запрос для получения уроков с заголовками
        lessons_response = s.post(
            f"https://{os.getenv('api_domain')}/api/student/courses/1147/lessons",
            headers=headers
        ).json()

    deadlines = []
    for lesson in lessons_response['lessons']:
        if lesson['deadline'] is None:
            continue
        deadlines.append((str(lesson['id']), lesson['title'], lesson['deadline'].split()[0]))

    return deadlines
