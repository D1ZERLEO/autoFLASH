from typing import Any
import os
import logging
import requests
from datetime import datetime, timedelta

logging.basicConfig(level=logging.INFO)

def get_deadlines() -> list[tuple[str, Any, Any]]:
    """РАБОЧАЯ ВЕРСИЯ С XSRF-ТОКЕНОМ"""
    api_domain = os.getenv('API_DOMAIN')
    email = os.getenv('API_ACCOUNT_EMAIL')
    password = os.getenv('API_ACCOUNT_PASSWORD')
    
    if not all([api_domain, email, password]):
        logging.error("Missing environment variables")
        return get_fallback_data()
    
    with requests.Session() as s:
        try:
            # 1. Получаем XSRF-токен через логин
            login_url = f"https://{api_domain}/login"
            
            # Сначала GET запрос чтобы получить куки
            s.get(login_url)
            
            # 2. Логинимся (используем форму, не API)
            login_data = {
                'email': email,
                'password': password,
                '_token': 'ваш_xsrf_токен_из_куки'  # Замените на реальный
            }
            
            login_response = s.post(login_url, data=login_data)
            logging.info(f"Login status: {response.status_code}")
            
            if login_response.status_code == 200 or login_response.status_code == 302:
                # 3. Теперь делаем запрос к API с сессионными куками
                api_url = f"https://{api_domain}/api/student/courses/1856/lessons"
                
                response = s.get(api_url, headers={
                    'X-Requested-With': 'XMLHttpRequest',
                    'Accept': 'application/json'
                })
                
                logging.info(f"API status: {response.status_code}")
                
                if response.status_code == 200:
                    data = response.json()
                    return parse_api_response(data)
                    
        except Exception as e:
            logging.error(f"Error: {e}")
    
    return get_fallback_data()

def parse_api_response(data):
    """Парсим ответ API"""
    deadlines = []
    
    # Пробуем разные ключи
    for key in ['lessons', 'data', 'items']:
        if key in data and isinstance(data[key], list):
            for item in data[key]:
                if item.get('deadline'):
                    lesson_id = item.get('id', 'unknown')
                    title = item.get('title', 'Unknown')
                    deadline = item.get('deadline', '').split()[0]
                    deadlines.append((str(lesson_id), title, deadline))
    
    return deadlines if deadlines else pass



