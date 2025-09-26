from bs4 import BeautifulSoup
from functools import reduce

from google_tables.to_table import write
from school_website.get_api_homeworks import get_homeworks

import os


def write_lesson_homework(lesson_id, lesson_title, deadline):
    page = get_homeworks(lesson_id)
    print(page.status_code)
    print(page.url)
    print(page.text[:2000])
    
    soup = BeautifulSoup(page.text, "html.parser")

    print(f'Made all of the requests to the {os.getenv("API_DOMAIN")}!')

    print('Collect information about students...')
    students = []
    for row in soup.findAll('tr', class_='odd'):
        items = row.findAll('td')
        name = items[2].contents[0].replace('\n', '').strip(' ')

        about_guy = [name]
        for hmw in items[6:]:
            _spans = hmw.findAll('span')
            if len(_spans) > 1:
                tasks_completed = _spans[1].contents[0].split('/')[0]
            else:
                tasks_completed = 'не сдано'
            about_guy.append(tasks_completed)
        students.append(about_guy)

    students.sort(key=lambda x: (ord('A') <= ord(x[0][0].upper()) <= ord('Z'), x[0]))

    print('Make changes at table...')
    iterator = iter(reduce(lambda x, y: x + y, [k[1:] for k in students]))
    write(title=lesson_title, deadline=deadline, q_students=len(students), grades=iterator,
          totals=[''] * (len(students[0]) - 1))
