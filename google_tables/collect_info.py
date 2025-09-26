from bs4 import BeautifulSoup
from functools import reduce
from google_tables.to_table import write
from school_website.get_api_homeworks import get_homeworks
import os

def write_lesson_homework(s, lesson_id, lesson_title, deadline):
    page = get_homeworks(s, lesson_id)
    soup = BeautifulSoup(page.text, "html.parser")

    students = []
    for row in soup.findAll('tr', class_='odd'):
        items = row.findAll('td')
        name = items[2].get_text(strip=True)
        about_guy = [name]
        for hmw in items[6:]:
            spans = hmw.findAll('span')
            if len(spans) > 1:
                tasks_completed = spans[1].get_text(strip=True).split('/')[0]
            else:
                tasks_completed = 'не сдано'
            about_guy.append(tasks_completed)
        students.append(about_guy)

    students.sort(key=lambda x: (ord('A') <= ord(x[0][0].upper()) <= ord('Z'), x[0]))

    iterator = iter(reduce(lambda x, y: x + y, [k[1:] for k in students]))
    write(
        title=lesson_title,
        deadline=deadline,
        q_students=len(students),
        grades=iterator,
        totals=[''] * (len(students[0]) - 1)
    )
