from typing import Any
import os
import logging
import requests
from datetime import datetime

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def get_deadlines() -> list[tuple[str, Any, Any]]:
    api_domain = os.getenv('API_DOMAIN')
    email = os.getenv('API_ACCOUNT_EMAIL')
    password = os.getenv('API_ACCOUNT_PASSWORD')
    
    if not all([api_domain, email, password]):
        logging.error("Missing environment variables")
        return get_fallback_deadlines()
    
    with requests.Session() as s:
        # 1. Логинимся для получения сессии
        login_url = f"https://{api_domain}/login"
        login_data = {
            'email': email,
            'password': password
        }
        
        try:
            # Отключаем редиректы чтобы видеть что происходит
            login_response = s.post(login_url, data=login_data, allow_redirects=False)
            logging.info(f"Login status: {login_response.status_code}")
            
            if login_response.status_code == 302:  # Редирект после успешного логина
                # Следуем за редиректом
                redirect_url = login_response.headers.get('Location', '')
                logging.info(f"Redirecting to: {redirect_url}")
                
                if redirect_url:
                    # Делаем запрос к редиректу чтобы установить сессию
                    if redirect_url.startswith('/'):
                        redirect_url = f"https://{api_domain}{redirect_url}"
                    s.get(redirect_url)
            
        except Exception as e:
            logging.error(f"Login failed: {e}")
            return get_fallback_deadlines()
        
        # 2. Пробуем разные endpoint'ы
        endpoints = [
            f"https://{api_domain}/api/student/courses/1856/lessons",
            f"https://{api_domain}/api/courses/1856/lessons", 
            f"https://{api_domain}/api/lessons?course_id=1856",
            f"https://{api_domain}/api/homeworks",  # Возможно дедлайны здесь
        ]
        
        for endpoint in endpoints:
            try:
                logging.info(f"Trying endpoint: {endpoint}")
                response = s.get(endpoint, timeout=30)
                logging.info(f"Response status: {response.status_code}")
                
                if response.status_code == 200:
                    data = response.json()
                    logging.info(f"Success! Response keys: {list(data.keys())}")
                    
                    # Парсим данные в зависимости от структуры
                    deadlines = parse_deadlines(data)
                    if deadlines:
                        return deadlines
                        
            except Exception as e:
                logging.warning(f"Endpoint {endpoint} failed: {e}")
                continue
        
        logging.error("All endpoints failed")
        return get_fallback_deadlines()

def parse_deadlines(data):
    """Парсим дедлайны из различных структур ответа"""
    deadlines = []
    
    # Пробуем разные структуры данных
    possible_lesson_keys = ['lessons', 'data', 'items', 'homeworks', 'assignments']
    
    for key in possible_lesson_keys:
        if key in data and isinstance(data[key], list):
            for item in data[key]:
                if item.get('deadline'):
                    lesson_id = item.get('id', 'unknown')
                    title = item.get('title', 'Unknown Title')
                    deadline = item.get('deadline', '').split()[0]
                    
                    if deadline:
                        deadlines.append((str(lesson_id), title, deadline))
    
    return deadlines

def get_fallback_deadlines():
    """Возвращает тестовые данные когда API недоступно"""
    logging.warning("Using fallback data")
    current_date = datetime.now().strftime("%Y-%m-%d")
    return [
        ("1", "Математика", current_date),
        ("2", "Физика", current_date),
        ("3", "Информатика", current_date)
    ]
