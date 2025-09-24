from typing import Any
import os

import requests


def get_auth_token():
    """Получение токена через логин и пароль"""
    api_domain = os.getenv('API_DOMAIN')
    email = os.getenv('API_ACCOUNT_EMAIL')
    password = os.getenv('API_ACCOUNT_PASSWORD')

    login_url = f"https://{api_domain}/api/login"
    auth_data = {
        'email': email,
        'password': password
    }

    response = requests.post(login_url, json=auth_data)
    if response.status_code == 200:
        data = response.json()
        return data.get('access_token') or data.get('token')

    return None
def get_deadlines() -> list[tuple[str, Any, Any]]:
    # Запускаем сессию
    with requests.Session() as s:
        # Заголовки для запроса уроков
        headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json',
            'Authorization': get_auth_token()
            # Используем токен из заголовков, если он там есть
        }

        # Делаем POST запрос для получения уроков с заголовками
        print(os.getenv('API_DOMAIN'))
        lessons_response = s.post(
            f"https://{os.getenv('API_DOMAIN')}/api/student/courses/1856/lessons",
            headers=headers
        ).json()

    deadlines = []
    for lesson in lessons_response['lessons']:
        if lesson['deadline'] is None:
            continue
        deadlines.append((str(lesson['id']), lesson['title'], lesson['deadline'].split()[0]))

    return deadlines
