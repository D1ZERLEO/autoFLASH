from typing import Any
import os
import logging
import requests


def get_deadlines() -> list[tuple[str, Any, Any]]:
    # Запускаем сессию
    with requests.Session() as s:
        # Заголовки для запроса уроков
        headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json',
            'Authorization': 'Bearer 1938977|1wyh786iIQb7ehAe2rgT08HVPkOO5cHqPMPU6WAD'
        }

        # Делаем POST запрос для получения уроков с заголовками
        api_domain = os.getenv('API_DOMAIN')
        if not api_domain:
            logging.error("API_DOMAIN environment variable is not set")
            return []
            
        url = f"https://{api_domain}/api/student/courses/1147/lessons"
        logging.info(f"Making request to: {url}")
        
        try:
            response = s.post(url, headers=headers)
            response.raise_for_status()  # Проверяем статус код
            
            lessons_response = response.json()
            logging.info(f"API response: {lessons_response}")
            
            # Проверяем структуру ответа
            if 'lessons' not in lessons_response:
                logging.error(f"Key 'lessons' not found in response. Available keys: {list(lessons_response.keys())}")
                return []
                
        except requests.exceptions.RequestException as e:
            logging.error(f"Request failed: {e}")
            return []
        except ValueError as e:
            logging.error(f"JSON decode error: {e}")
            return []

    deadlines = []
    for lesson in lessons_response['lessons']:
        if lesson.get('deadline') is None:
            continue
        # Безопасное извлечение данных
        lesson_id = lesson.get('id')
        title = lesson.get('title')
        deadline = lesson.get('deadline', '').split()[0] if lesson.get('deadline') else None
        
        if lesson_id and title and deadline:
            deadlines.append((str(lesson_id), title, deadline))

    logging.info(f"Found {len(deadlines)} deadlines")
    return deadlines
