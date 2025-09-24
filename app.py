from dotenv import load_dotenv
import logging
import sys

from vk.send_message import send_deadline_message
from school_website.about_deadlines import get_deadlines
from google_tables.to_table import get_last_deadline
from google_tables.collect_info import write_lesson_homework
from dates import filter_dates_by_today, filter_dates_in_range, sort_by_date

# Настройка логирования
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


def deadline_sender(deadlines_list):
    if not deadlines_list:
        logging.warning("No deadlines to send")
        return
        
    for lesson_title in filter_dates_by_today(deadlines_list):
        send_deadline_message(lesson_title)


def add_to_the_table(deadlines_list):
    if not deadlines_list:
        logging.warning("No deadlines to add to table")
        return
        
    try:
        last_deadline = get_last_deadline()
        for lesson_id, lesson_title, deadline in filter_dates_in_range(
                deadlines_list, last_deadline=last_deadline
        ):
            write_lesson_homework(lesson_id, lesson_title, deadline)
    except Exception as e:
        logging.error(f"Error adding to table: {e}")


if __name__ == "__main__":
    load_dotenv()
    
    try:
        deadlines = get_deadlines()
        if not deadlines:
            logging.warning("No deadlines received from API")
            sys.exit(0)
            
        sorted_deadlines = sort_by_date(deadlines)
        deadline_sender(sorted_deadlines)
        add_to_the_table(sorted_deadlines)
        
    except Exception as e:
        logging.error(f"Application failed: {e}")
        sys.exit(1)
