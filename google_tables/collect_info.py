from bs4 import BeautifulSoup
from functools import reduce

from google_tables.to_table import write
from school_website.get_api_homeworks import get_homeworks

import os

def write_lesson_homework(s, lesson_id, lesson_title, deadline):
    page = get_homeworks(s, lesson_id)

    soup = BeautifulSoup(page.text, "html.parser")
    print(f'Made all of the requests to the {os.getenv("API_DOMAIN")}!')

    print('Collect information about students...')
    students = []

    for row in soup.findAll('tr', class_='odd'):
        items = row.findAll('td')
        if len(items) < 7:
            continue

        name = items[2].get_text(strip=True)
        about_guy = [name]

        # идём по всем домашкам, начиная с 6-го индекса
        for hmw in items[6:]:
            # проверяем, есть ли ссылка с результатами
            link = hmw.find("a", href=True)
            if link:
                spans = [sp.get_text(strip=True) for sp in link.find_all("span")]
                if spans:
                    # обычно первый span = "6/6", второй = "100%"
                    about_guy.append(spans[0])  
                else:
                    about_guy.append("сдано (но без деталей)")
            else:
                # если ссылка нет, значит статусом управляет <span>
                span = hmw.find("span")
                if span:
                    about_guy.append(span.get_text(strip=True))
                else:
                    about_guy.append("нет данных")

        students.append(about_guy)

    # сортировка студентов: сначала A-Z английские, потом остальные
    students.sort(key=lambda x: (ord('A') <= ord(x[0][0].upper()) <= ord('Z'), x[0]))

    print('Make changes at table...')
    from functools import reduce
    iterator = iter(reduce(lambda x, y: x + y, [k[1:] for k in students]))
    from google_tables.to_table import write
    write(
        title=lesson_title,
        deadline=deadline,
        q_students=len(students),
        grades=iterator,
        totals=[''] * (len(students[0]) - 1)
    )
