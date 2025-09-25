from typing import Any
import os
import requests
from bs4 import BeautifulSoup

def get_deadlines() -> list[tuple[str, Any, Any]]:
    # Получаем учетные данные из переменных окружения
    email = os.getenv('API_ACCOUNT_EMAIL')
    password = os.getenv('API_ACCOUNT_PASSWORD')
    
    if not email or not password:
        raise Exception("Не заданы переменные окружения API_ACCOUNT_EMAIL и/или API_ACCOUNT_PASSWORD")
    
    # Создаем сессию для сохранения cookies
    session = requests.Session()
    
    # Шаг 1: Получаем страницу логина для извлечения CSRF-токена
    login_page_url = "https://admin.100points.ru/login"
    login_page_response = session.get(login_page_url)
    
    if login_page_response.status_code != 200:
        raise Exception(f"Ошибка загрузки страницы логина: {login_page_response.status_code}")
    
    # Парсим CSRF-токен из формы
    soup = BeautifulSoup(login_page_response.content, 'html.parser')
    csrf_token = soup.find('input', {'name': '_token'})
    
    if not csrf_token:
        # Попробуем найти CSRF-токен в meta-тегах
        csrf_meta = soup.find('meta', {'name': 'csrf-token'})
        if csrf_meta:
            csrf_token_value = csrf_meta.get('content')
        else:
            raise Exception("Не удалось найти CSRF-токен на странице логина")
    else:
        csrf_token_value = csrf_token.get('value')
    
    # Шаг 2: Выполняем авторизацию
    login_data = {
        'email': email,
        'password': password,
        '_token': csrf_token_value
    }
    
    login_response = session.post(login_page_url, data=login_data, allow_redirects=False)
    
    # Проверяем редирект после авторизации (успешный вход обычно редиректит)
    if login_response.status_code != 302:
        raise Exception(f"Ошибка авторизации: {login_response.status_code}")
    
    # Шаг 3: Получаем страницу журнала
    journal_url = "https://admin.100points.ru/student_live/index"
    journal_response = session.get(journal_url)
    
    if journal_response.status_code != 200:
        raise Exception(f"Ошибка загрузки страницы журнала: {journal_response.status_code}")
    
    # Парсим HTML журнала
    soup = BeautifulSoup(journal_response.content, 'html.parser')
    
    deadlines = []
    
    # Находим все строки с уроками в таблице
    lesson_rows = soup.select('thead tr:first-child th[data-lesson-id]')
    
    for lesson_row in lesson_rows:
        lesson_id = lesson_row.get('data-lesson-id')
        title = lesson_row.get_text(strip=True)
        
        # Ищем соответствующий дедлайн в таблице
        deadline_elem = soup.find('b', id=lambda x: x and x.startswith(f'deadline_{lesson_id}'))
        
        if deadline_elem:
            deadline_datetime = deadline_elem.get('data-datetime', '')
            # Берем только дату (первую часть до T)
            deadline_date = deadline_datetime.split('T')[0] if deadline_datetime else ''
            
            if deadline_date:
                deadlines.append((lesson_id, title, deadline_date))
    
    return deadlines
