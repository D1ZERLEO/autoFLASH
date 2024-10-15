from vk.send_message import send_deadline_message
from points100.about_deadlines import get_deadlines
from google_tables.to_table import get_last_deadline
from google_tables.collect_info import write_lesson_homework

from dates import filter_dates_by_today, filter_dates_in_range


def deadline_sender(deadlines_list):
    for lesson_title in filter_dates_by_today(deadlines_list):
        send_deadline_message(lesson_title)


def add_to_the_table(deadlines_list):
    for lesson_id, deadline in filter_dates_in_range(
            deadlines_list, last_deadline=get_last_deadline()
    ):
        write_lesson_homework(lesson_id, deadline)


if __name__ == "__main__":
    deadlines = get_deadlines()
    deadline_sender(deadlines)
    add_to_the_table(deadlines)
