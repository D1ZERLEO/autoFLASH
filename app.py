from dotenv import load_dotenv
import requests

from vk.send_message import send_deadline_message
from school_website.about_deadlines import get_deadlines
from school_website.get_api_homeworks import get_homeworks
from google_tables.to_table import get_last_deadline
from google_tables.collect_info import write_lesson_homework
from dates import filter_dates_by_today, filter_dates_in_range, sort_by_date

def deadline_sender(deadlines_list):
    for lesson_title in filter_dates_by_today(deadlines_list):
        send_deadline_message(lesson_title)

def add_to_the_table(s, deadlines_list):
    for lesson_id, lesson_title, deadline in filter_dates_in_range(
            deadlines_list, last_deadline=get_last_deadline()
    ):
        page = get_homeworks(s, lesson_id)
        print(f"{lesson_title}: {page.status_code}")  # можно проверять статус
        write_lesson_homework(s, lesson_id, lesson_title, deadline)

if __name__ == "__main__":
    load_dotenv()
    with requests.Session() as s:
        deadlines = sort_by_date(get_deadlines(s))  # логин выполняется здесь один раз
        deadline_sender(deadlines)
        add_to_the_table(s, deadlines)
