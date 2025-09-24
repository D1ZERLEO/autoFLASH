from typing import Any
import os
import logging
import requests
import json

# Настройка логирования
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

de get_deadlines() -> list[tuple[str, Any, Any]]:
    api_domain = os.getenv('API_DOMAIN')
    course_id = "1856"  # Из вашего URL
    
    if not api_domain:
        logging.error("API_DOMAIN environment variable is not set")
        return []

    # Проверяем учетные данные для входа
    email = os.getenv('API_ACCOUNT_EMAIL')
    password = os.getenv('API_ACCOUNT_PASSWORD')
    
    if not email or not password:
        logging.error("API_ACCOUNT_EMAIL or API_ACCOUNT_PASSWORD not set")
        return []

    with requests.Session() as s:
        # 1. Сначала попробуем авторизоваться
        login_url = f"https://{api_domain}/api/login"
        login_data = {
            'email': email,
            'password': password
        }
        
        try:
            logging.info(f"Attempting login with email: {email}")
            login_response = s.post(login_url, json=login_data)
            logging.info(f"Login status: {login_response.status_code}")
            logging.info(f"Login response headers: {dict(login_response.headers)}")
            
            if login_response.status_code != 200:
                logging.error(f"Login failed: {login_response.text}")
                return []
                
            # Проверяем, получили ли мы токен или сессию
            login_data = login_response.json()
            logging.info(f"Login response: {login_data}")
            
        except Exception as e:
            logging.error(f"Login error: {e}")
            return []

        # 2. Теперь пробуем получить уроки разными способами
        
        # Вариант 1: Токен из заголовков + GET запрос
        headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json',
            'Authorization': 'Bearer 1938977|1wyh786iIQb7ehAe2rgT08HVPkOO5cHqPMPU6WAD'
        }
        
        urls_to_try = [
            f"https://{api_domain}/api/student/courses/{course_id}/lessons",
            f"https://{api_domain}/api/courses/{course_id}/lessons",
            f"https://{api_domain}/api/lessons?course_id={course_id}",
        ]
        
        for url in urls_to_try:
            logging.info(f"Trying URL: {url}")
            
            for method in [s.get, s.post]:
                try:
                    logging.info(f"Trying {method.__name__.upper()} request")
                    
                    if method == s.get:
                        response = method(url, headers=headers)
                    else:
                        response = method(url, headers=headers, json={})
                    
                    logging.info(f"Response status: {response.status_code}")
                    logging.info(f"Response headers: {dict(response.headers)}")
                    
                    if response.status_code == 200:
                        data = response.json()
                        logging.info(f"Success! Response keys: {list(data.keys())}")
                        logging.info(f"Response sample: {json.dumps(data, ensure_ascii=False)[:500]}...")
                        
                        # Пытаемся найти уроки в ответе
                        lessons = None
                        for key in ['lessons', 'data', 'items', 'results']:
                            if key in data:
                                lessons = data[key]
                                logging.info(f"Found lessons in key: {key}")
                                break
                        
                        if lessons:
                            deadlines = []
                            for lesson in lessons:
                                if lesson.get('deadline') is None:
                                    continue
                                    
                                lesson_id = lesson.get('id')
                                title = lesson.get('title')
                                deadline = lesson.get('deadline', '').split()[0] if lesson.get('deadline') else None
                                
                                if lesson_id and title and deadline:
                                    deadlines.append((str(lesson_id), title, deadline))
                            
                            logging.info(f"Processed {len(deadlines)} deadlines")
                            return deadlines
                        else:
                            logging.warning(f"No lessons found in response. Available keys: {list(data.keys())}")
                    
                    else:
                        logging.error(f"Error {response.status_code}: {response.text}")
                        
                except Exception as e:
                    logging.error(f"Request failed: {e}")
                    continue

        logging.error("All attempts failed")
        return []

if __name__ == "__main__":
    # Тестируем функцию
    from dotenv import load_dotenv
    load_dotenv()
    
    deadlines = get_deadlines()
    print(f"Found {len(deadlines)} deadlines")
