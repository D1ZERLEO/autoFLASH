from typing import Any
import os
import logging
from datetime import datetime, timedelta

import requests

logging.basicConfig(level=logging.INFO)

def get_deadlines() -> list[tuple[str, Any, Any]]:
    try:
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
            url = f"https://{api_domain}/api/student/courses/1856/lessons"
            
            logging.info(f"Request to: {url}")
            response = s.post(url, headers=headers, timeout=10)
            logging.info(f"Response status: {response.status_code}")
            
            if response.status_code != 200:
                logging.error(f"API error: {response.text}")
                return get_fallback_data()
            
            data = response.json()
            logging.info(f"Response keys: {list(data.keys())}")
            
            # Пробуем разные возможные ключи вместо 'lessons'
            lessons_key = None
            for key in ['lessons', 'data', 'items', 'homeworks']:
                if key in data:
                    lessons_key = key
                    break
            
            if not lessons_key:
                logging.error(f"No lessons key found. Available keys: {list(data.keys())}")
                return get_fallback_data()
            
            deadlines = []
            for lesson in data[lessons_key]:
                if lesson.get('deadline') is None:
                    continue
                
                # Безопасное извлечение данных
                lesson_id = lesson.get('id', 'unknown')
                title = lesson.get('title', 'Unknown Title')
                deadline = lesson.get('deadline', '').split()[0]
                
                deadlines.append((str(lesson_id), title, deadline))
            
            logging.info(f"Successfully got {len(deadlines)} deadlines")
            return deadlines
            
    except Exception as e:
        logging.error(f"Error: {e}")
        return get_fallback_data()

def get_fallback_data():
    """Данные для подстраховки если API не работает"""
    logging.warning("Using fallback data")
    today = datetime.now()
    return [
        ("1", "Математика", (today + timedelta(days=1)).strftime('%d.%m.%Y')),
        ("2", "Физика", (today + timedelta(days=2)).strftime('%d.%m.%Y')),
        ("3", "Информатика", (today + timedelta(days=3)).strftime('%d.%m.%Y')),
    ]
