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
        # Добавим параметры, чтобы получить данные для конкретного курса
        journal_url = "https://admin.100points.ru/student_live/index"
        params = {
            'subject_id': '20',  # Информатика с Артёмом (из вашего HTML)
            'course_id': '1856',  # Годовой курс по информатике
        }
        
        logger.info(f"Загрузка страницы журнала с параметрами: {params}")
        journal_response = session.get(journal_url, params=params)
        
        if journal_response.status_code != 200:
            logger.error(f"Ошибка загрузки страницы журнала: {journal_response.status_code}")
            return []
        
        # Парсим HTML журнала
        soup = BeautifulSoup(journal_response.content, 'html.parser')
        
        # Сохраним HTML для отладки
        with open('debug_journal.html', 'w', encoding='utf-8') as f:
            f.write(journal_response.text)
        logger.info("Сохранен HTML страницы журнала в debug_journal.html")
        
        # Анализ структуры страницы
        logger.info("Анализ структуры страницы:")
        
        # Проверим наличие основных элементов
        title = soup.find('title')
        if title:
            logger.info(f"Заголовок страницы: {title.get_text()}")
        
        # Поиск таблицы разными способами
        tables = soup.find_all('table')
        logger.info(f"Найдено таблиц на странице: {len(tables)}")
        
        for i, table in enumerate(tables):
            logger.info(f"Таблица {i+1}: классы - {table.get('class', [])}")
        
        # Попробуем разные селекторы для поиска уроков
        selectors = [
            'thead tr:first-child th[data-lesson-id]',
            'th[data-lesson-id]',
            '[data-lesson-id]',
            'thead th',
            '.table th',
            'table th'
        ]
        
        deadlines = []
        
        for selector in selectors:
            lesson_rows = soup.select(selector)
            logger.info(f"Селектор '{selector}': найдено {len(lesson_rows)} элементов")
            
            if lesson_rows:
                for i, lesson_row in enumerate(lesson_rows):
                    lesson_id = lesson_row.get('data-lesson-id')
                    title = lesson_row.get_text(strip=True)
                    
                    if lesson_id:  # Только если есть ID урока
                        logger.info(f"Урок {i+1}: ID={lesson_id}, Название={title}")
                        
                        # Ищем соответствующий дедлайн
                        deadline_elems = soup.find_all('b', id=lambda x: x and f'deadline_{lesson_id}' in x)
                        
                        for deadline_elem in deadline_elems:
                            deadline_datetime = deadline_elem.get('data-datetime', '')
                            deadline_date = deadline_datetime.split('T')[0] if deadline_datetime else ''
                            
                            if deadline_date:
                                deadlines.append((lesson_id, title, deadline_date))
                                logger.info(f"Дедлайн для урока {lesson_id}: {deadline_date}")
        
        # Если не нашли через селекторы, попробуем найти по структуре таблицы
        if not deadlines:
            logger.info("Поиск по структуре таблицы...")
            
            # Попробуем найти строки с дедлайнами по другим признакам
            deadline_elems = soup.find_all('b', id=lambda x: x and 'deadline' in x)
            logger.info(f"Найдено элементов с дедлайнами: {len(deadline_elems)}")
            
            for elem in deadline_elems:
                deadline_datetime = elem.get('data-datetime', '')
                if deadline_datetime:
                    deadline_date = deadline_datetime.split('T')[0]
                    # Попробуем найти связанный урок
                    lesson_id = elem.get('id', '').replace('deadline_', '').split('user_id')[0]
                    if lesson_id:
                        deadlines.append((lesson_id, f"Урок {lesson_id}", deadline_date))
                        logger.info(f"Найден дедлайн: урок {lesson_id}, дата {deadline_date}")
        
        logger.info(f"Итого собрано дедлайнов: {len(deadlines)}")
        return deadlines
        
    except Exception as e:
        logger.error(f"Исключение в get_deadlines: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return []
