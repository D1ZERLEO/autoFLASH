import os
import requests
from bs4 import BeautifulSoup
import logging

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
            # Сохраним HTML для отладки
            with open('debug_login.html', 'w', encoding='utf-8') as f:
                f.write(login_page_response.text)
            logger.info("Сохранен HTML страницы логина в debug_login.html")
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
        
        # Шаг 3: Получаем страницу журнала
        journal_url = "https://admin.100points.ru/student_live/index"
        logger.info(f"Загрузка страницы журнала: {journal_url}")
        journal_response = session.get(journal_url)
        
        if journal_response.status_code != 200:
            logger.error(f"Ошибка загрузки страницы журнала: {journal_response.status_code}")
            return []
        
        # Парсим HTML журнала
        soup = BeautifulSoup(journal_response.content, 'html.parser')
        
        # Сохраним HTML для отладки
        with open('debug_journal.html', 'w', encoding='utf-8') as f:
            f.write(journal_response.text)
        logger.info("Сохранен HTML страницы журнала в debug_journal.html")
        
        deadlines = []
        
        # Находим все строки с уроками в таблице
        lesson_rows = soup.select('thead tr:first-child th[data-lesson-id]')
        logger.info(f"Найдено уроков в заголовке: {len(lesson_rows)}")
        
        for i, lesson_row in enumerate(lesson_rows):
            lesson_id = lesson_row.get('data-lesson-id')
            title = lesson_row.get_text(strip=True)
            logger.info(f"Урок {i+1}: ID={lesson_id}, Название={title}")
            
            # Ищем соответствующий дедлайн в таблице
            deadline_elem = soup.find('b', id=lambda x: x and x.startswith(f'deadline_{lesson_id}'))
            
            if deadline_elem:
                deadline_datetime = deadline_elem.get('data-datetime', '')
                # Берем только дату (первую часть до T)
                deadline_date = deadline_datetime.split('T')[0] if deadline_datetime else ''
                
                if deadline_date:
                    deadlines.append((lesson_id, title, deadline_date))
                    logger.info(f"Дедлайн для урока {lesson_id}: {deadline_date}")
                else:
                    logger.warning(f"Не удалось извлечь дату для урока {lesson_id}")
            else:
                logger.warning(f"Не найден элемент дедлайна для урока {lesson_id}")
        
        logger.info(f"Итого собрано дедлайнов: {len(deadlines)}")
        return deadlines
        
    except Exception as e:
        logger.error(f"Исключение в get_deadlines: {e}")
        return []
