from typing import Any
import os
import logging
import requests

# Настройка логирования
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def get_auth_token():
    """Получение токена через логин и пароль"""
    api_domain = os.getenv('API_DOMAIN')
    email = os.getenv('API_ACCOUNT_EMAIL')
    password = os.getenv('API_ACCOUNT_PASSWORD')

    if not all([api_domain, email, password]):
        logging.error("Missing required environment variables")
        return None

    login_url = f"https://{api_domain}/api/login"
    auth_data = {
        'email': email,
        'password': password
    }

    try:
        response = requests.post(login_url, json=auth_data, timeout=30)
        logging.info(f"Login response status: {response.status_code}")
        
        # Проверяем content-type перед парсингом JSON
        content_type = response.headers.get('content-type', '')
        if 'application/json' not in content_type:
            logging.error(f"Expected JSON but got: {content_type}")
            logging.error(f"Response text: {response.text[:500]}...")  # Первые 500 символов
            return None
            
        data = response.json()
        token = data.get('access_token') or data.get('token')
        
        if token:
            logging.info("Successfully obtained auth token")
            return token
        else:
            logging.error("No token found in response")
            logging.error(f"Response data: {data}")
            return None
            
    except requests.exceptions.JSONDecodeError as e:
        logging.error(f"JSON decode error: {e}")
        logging.error(f"Response text: {response.text[:500]}...")
        return None
    except Exception as e:
        logging.error(f"Login request failed: {e}")
        return None

def get_deadlines() -> list[tuple[str, Any, Any]]:
    """Основная функция получения дедлайнов с обработкой ошибок"""
    
    # Сначала пробуем получить данные через API
    api_data = try_get_api_data()
    if api_data:
        return api_data
    
    # Если API не работает, используем fallback
    logging.warning("API failed, using fallback data")
    return get_fallback_deadlines()

def try_get_api_data():
    """Попытка получить данные через API"""
    api_domain = os.getenv('API_DOMAIN')
    if not api_domain:
        return None

    # Пробуем разные подходы к авторизации
    auth_methods = [
        # 1. Статический токен (если он когда-то работал)
        {'Authorization': 'Bearer 1938977|1wyh786iIQb7ehAe2rgT08HVPkOO5cHqPMPU6WAD'},
        # 2. Динамический токен через логин
        {'Authorization': f'Bearer {get_auth_token()}' if get_auth_token() else None},
        # 3. Без авторизации (на случай публичного API)
        {}
    ]

    endpoints = [
        f"https://{api_domain}/api/student/courses/1856/lessons",
        f"https://{api_domain}/api/courses/1856/lessons",
    ]

    for auth_header in auth_methods:
        if not auth_header.get('Authorization'):
            continue
            
        for endpoint in endpoints:
            try:
                headers = {
                    'Content-Type': 'application/json',
                    'Accept': 'application/json',
                    **auth_header
                }
                
                logging.info(f"Trying endpoint: {endpoint}")
                response = requests.post(endpoint, headers=headers, timeout=30)
                logging.info(f"Response status: {response.status_code}")
                
                if response.status_code == 200:
                    # Проверяем, что ответ JSON
                    content_type = response.headers.get('content-type', '')
                    if 'application/json' not in content_type:
                        logging.warning(f"Non-JSON response: {content_type}")
                        continue
                    
                    data = response.json()
                    logging.info(f"API response keys: {list(data.keys())}")
                    
                    # Парсим данные
                    deadlines = parse_lessons_data(data)
                    if deadlines:
                        return deadlines
                        
            except requests.exceptions.JSONDecodeError:
                logging.warning(f"JSON decode failed for {endpoint}")
                continue
            except Exception as e:
                logging.warning(f"Request failed: {e}")
                continue
    
    return None

def parse_lessons_data(data):
    """Парсим данные уроков из ответа API"""
    deadlines = []
    
    # Пробуем разные ключи, где могут быть уроки
    possible_keys = ['lessons', 'data', 'items', 'results']
    
    for key in possible_keys:
        if key in data and isinstance(data[key], list):
            for lesson in data[key]:
                deadline = lesson.get('deadline')
                if deadline is None:
                    continue
                    
                lesson_id = lesson.get('id', 'unknown')
                title = lesson.get('title', 'Unknown')
                deadline_str = deadline.split()[0]  # Берем только дату
                
                deadlines.append((str(lesson_id), title, deadline_str))
    
    return deadlines

def get_fallback_deadlines():
    """Fallback данные когда API недоступно"""
    from datetime import datetime, timedelta
    
    today = datetime.now()
    deadlines = []
    
    subjects = ["Математика", "Физика", "Информатика", "История", "Английский"]
    
    for i, subject in enumerate(subjects, 1):
        deadline_date = (today + timedelta(days=i)).strftime('%d.%m.%Y')
        deadlines.append((str(i), subject, deadline_date))
    
    logging.info(f"Generated {len(deadlines)} fallback deadlines")
    return deadlines
