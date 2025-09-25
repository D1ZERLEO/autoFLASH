import os
import requests
from bs4 import BeautifulSoup
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

def get_deadlines():
    # Получаем учетные данные из переменных окружения
    email = os.getenv('API_ACCOUNT_EMAIL')
    password = os.getenv('API_ACCOUNT_PASSWORD')
    
    if not email or not password:
        logger.error("Не заданы переменные окружения API_ACCOUNT_EMAIL и/или API_ACCOUNT_PASSWORD")
        return []
    
    logger.info(f"Авторизация для пользователя: {email}")
    
    # Создаем сессию для сохранения cookies
    session = requests.Session()
    
    try:
        # Шаг 1: Получаем страницу логина для извлечения CSRF-токена
        login_page_url = "https://admin.100points.ru/login"
        logger.info(f"Загрузка страницы логина: {login_page_url}")
        login_page_response = session.get(login_page_url)
        
        if login_page_response.status_code != 200:
            logger.error(f"Ошибка загрузки страницы логина: {login_page_response.status_code}")
            return []
        
        # Парсим CSRF-токен из формы
        soup = BeautifulSoup(login_page_response.content, 'html.parser')
        csrf_token = soup.find('input', {'name': '_token'})
        
        if not csrf_token:
            logger.error("Не удалось найти CSRF-токен на странице логина")
            return []
        
        csrf_token_value = csrf_token.get('value')
        logger.info("CSRF-токен найден")
        
        # Шаг 2: Выполняем авторизацию
        login_data = {
            'email': email,
            'password': password,
            '_token': csrf_token_value
        }
        
        logger.info("Отправка данных авторизации...")
        login_response = session.post(login_page_url, data=login_data, allow_redirects=True)
        
        # Проверяем, успешна ли авторизация
        if "login" in login_response.url:
            logger.error("Ошибка авторизации: остались на странице логина")
            return []
        
        logger.info("Авторизация успешна")
        
        # Шаг 3: Получаем страницу журнала с параметрами фильтрации
        journal_url = "https://admin.100points.ru/student_live/index"
        params = {
            'subject_id': '20',
            'course_id': '1856',
        }
        
        logger.info(f"Загрузка страницы журнала с параметрами: {params}")
        journal_response = session.get(journal_url, params=params)
        
        if journal_response.status_code != 200:
            logger.error(f"Ошибка загрузки страницы журнала: {journal_response.status_code}")
            return []
        
        # Парсим HTML журнала
        soup = BeautifulSoup(journal_response.content, 'html.parser')
        
        deadlines = []
        
        # Находим все уроки в заголовке таблицы
        lesson_rows = soup.select('thead tr:first-child th[data-lesson-id]')
        logger.info(f"Найдено уроков в заголовке: {len(lesson_rows)}")
        
        for i, lesson_row in enumerate(lesson_rows):
            lesson_id = lesson_row.get('data-lesson-id')
            title = lesson_row.get_text(strip=True)
            
            if lesson_id:
                logger.info(f"Урок {i+1}: ID={lesson_id}, Название={title}")
                
                # Ищем соответствующий дедлайн
                deadline_elems = soup.find_all('b', id=lambda x: x and f'deadline_{lesson_id}' in x)
                
                for deadline_elem in deadline_elems:
                    deadline_datetime = deadline_elem.get('data-datetime', '')
                    deadline_date = deadline_datetime.split('T')[0] if deadline_datetime else ''
                    
                    if deadline_date:
                        # Преобразуем дату из формата YYYY-MM-DD в DD.MM.YYYY
                        try:
                            date_obj = datetime.strptime(deadline_date, '%Y-%m-%d')
                            formatted_date = date_obj.strftime('%d.%m.%Y')
                            deadlines.append((lesson_id, title, formatted_date))
                            logger.info(f"Дедлайн для урока {lesson_id}: {formatted_date}")
                        except ValueError as e:
                            logger.error(f"Ошибка форматирования даты {deadline_date}: {e}")
        
        logger.info(f"Итого собрано дедлайнов: {len(deadlines)}")
        return deadlines
        
    except Exception as e:
        logger.error(f"Исключение в get_deadlines: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return []
