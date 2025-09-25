from typing import Any
import os

import requests


def get_deadlines() -> list[tuple[str, Any, Any]]:
    # Запускаем сессию
    with requests.Session() as s:
        # Заголовки для запроса уроков
        headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json',
            'Authorization': 'Bearer 1938977|1wyh786iIQb7ehAe2rgT08HVPkOO5cHqPMPU6WAD' # скорее всего проблемы тут
            # Используем токен из заголовков, если он там есть
        }

        # Делаем POST запрос для получения уроков с заголовками
        print(os.getenv('API_DOMAIN'))
        lessons_response = s.post(
            f"https://{os.getenv('API_DOMAIN')}/api/student/courses/1147/lessons", # еще тут 100% неправильно, потому что во-первых 1856, а во-вторых надо путь немного другой, возможно там student_live(не student)
            headers=headers
        ).json()
    print(lessons_response)  # что реально вернул сервер
    deadlines = []
    for lesson in lessons_response['lessons']: # падает всё на этой строке с отсылкой на get_deadlines()
        if lesson['deadline'] is None:
            continue
        deadlines.append((str(lesson['id']), lesson['title'], lesson['deadline'].split()[0]))

    return deadlines
