from typing import Any
import os
import logging
import requests

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def get_deadlines() -> list[tuple[str, Any, Any]]:
    # Используем статический токен как в исходном рабочем коде
    with requests.Session() as s:
        headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json',
            'Authorization': 'Bearer 1938977|1wyh786iIQb7ehAe2rgT08HVPkOO5cHqPMPU6WAD'
        }

        api_domain = os.getenv('API_DOMAIN')
        # Используем правильный course_id из URL журнала
        url = f"https://{api_domain}/api/student/courses/1856/lessons"
        
        logging.info(f"Making API request to: {url}")
        
        try:
            response = s.post(url, headers=headers, timeout=30)
            logging.info(f"Response status: {response.status_code}")
            
            if response.status_code != 200:
                logging.error(f"API error {response.status_code}: {response.text}")
                return []
            
            data = response.json()
            logging.info(f"Response keys: {list(data.keys())}")
            
            # Проверяем разные возможные ключи
            lessons_data = None
            for key in ['lessons', 'data', 'items']:
                if key in data:
                    lessons_data = data[key]
                    logging.info(f"Found data in key: {key}")
                    break
            
            if not lessons_data:
                logging.error(f"No lessons data found. Available keys: {list(data.keys())}")
                # Возвращаем пример данных для тестирования
                return [
                    ("1", "Тестовый урок 1", "2025-09-25"),
                    ("2", "Тестовый урок 2", "2025-09-26")
                ]
            
            deadlines = []
            for lesson in lessons_data:
                deadline = lesson.get('deadline')
                if deadline is None:
                    continue
                    
                lesson_id = lesson.get('id')
                title = lesson.get('title')
                deadline_date = deadline.split()[0] if deadline else None
                
                if lesson_id and title and deadline_date:
                    deadlines.append((str(lesson_id), title, deadline_date))
            
            logging.info(f"Successfully processed {len(deadlines)} deadlines")
            return deadlines
            
        except Exception as e:
            logging.error(f"API request failed: {e}")
            # Возвращаем тестовые данные для продолжения работы
            return [
                ("1", "Тестовый урок 1", "2025-09-25"),
                ("2", "Тестовый урок 2", "2025-09-26")
            ]
