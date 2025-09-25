import os
import logging
import sys
from dotenv import load_dotenv

from vk.send_message import send_deadline_message
from school_website.about_deadlines import get_deadlines
from google_tables.to_table import get_last_deadline
from google_tables.collect_info import write_lesson_homework

from dates import filter_dates_by_today, filter_dates_in_range, sort_by_date

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

def deadline_sender(deadlines_list):
    try:
        today_deadlines = filter_dates_by_today(deadlines_list)
        logger.info(f"Найдено дедлайнов на сегодня: {len(today_deadlines)}")
        
        for lesson_title in today_deadlines:
            logger.info(f"Отправка сообщения для: {lesson_title}")
            send_deadline_message(lesson_title)
            
    except Exception as e:
        logger.error(f"Ошибка в deadline_sender: {e}")
        raise

def add_to_the_table(deadlines_list):
    try:
        last_deadline = get_last_deadline()
        logger.info(f"Последний дедлайн в таблице: {last_deadline}")
        
        filtered_deadlines = filter_dates_in_range(
            deadlines_list, last_deadline=last_deadline
        )
        logger.info(f"Найдено дедлайнов для добавления: {len(filtered_deadlines)}")
        
        for lesson_id, lesson_title, deadline in filtered_deadlines:
            logger.info(f"Добавление в таблицу: {lesson_title} ({deadline})")
            write_lesson_homework(lesson_id, lesson_title, deadline)
            
    except Exception as e:
        logger.error(f"Ошибка в add_to_the_table: {e}")
        raise

def main():
    try:
        logger.info("Загрузка переменных окружения...")
        load_dotenv()
        
        # Проверка обязательных переменных
        required_vars = ['API_ACCOUNT_EMAIL', 'API_COUNT_PASSWORD', 'YOUR_GOOGLE_SHEET_TITLE']
        for var in required_vars:
            if not os.getenv(var):
                logger.error(f"Не установлена переменная окружения: {var}")
                return
        
        logger.info("Получение дедлайнов с сайта...")
        deadlines = get_deadlines()
        logger.info(f"Получено дедлайнов: {len(deadlines)}")
        
        if not deadlines:
            logger.warning("Не удалось получить дедлайны")
            return
            
        logger.info("Сортировка дедлайнов...")
        sorted_deadlines = sort_by_date(deadlines)
        
        logger.info("Отправка уведомлений...")
        deadline_sender(sorted_deadlines)
        
        logger.info("Добавление в таблицу...")
        add_to_the_table(sorted_deadlines)
        
        logger.info("Скрипт успешно завершен!")
        
    except Exception as e:
        logger.error(f"Критическая ошибка: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
