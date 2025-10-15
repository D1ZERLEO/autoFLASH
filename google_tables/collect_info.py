from bs4 import BeautifulSoup
from functools import reduce

from google_tables.to_table import write
from school_website.get_api_homeworks import get_homeworks

import os

def write_lesson_homework(s, lesson_id, lesson_title, deadline):
    # получаем страницу и уже готовый список домашних заданий
    page = get_homeworks(s, lesson_id)

    # вот тут лежат все отфильтрованные данные (только нужные ученики)
    parsed_homeworks = getattr(page, "parsed_homeworks", [])
    print(f'Made all of the requests to the {os.getenv("API_DOMAIN")}!')
    print(f'Всего найдено домашних: {len(parsed_homeworks)}')

    # если всё же parsed_homeworks пуст, можно fallback к html (для отладки)
    if not parsed_homeworks:
        print("⚠️ parsed_homeworks пуст — fallback к старому HTML-парсеру")
        soup = BeautifulSoup(page.text, "html.parser")
        tbody = soup.find("tbody", id="student_lives_body")
        parsed_homeworks = []
        if tbody:
            for a in tbody.find_all("a", href=True):
                href = a["href"]
                if "student_live/tasks" not in href:
                    continue
                spans = [sp.get_text(strip=True) for sp in a.find_all("span")]
                parsed_homeworks.append((href, spans, None))

    # теперь превращаем parsed_homeworks в таблицу (students)
    print('Collect information about students...')
    students = []
    for href, spans, dt in parsed_homeworks:
        name = spans[0] if spans else "Без имени"
        about_guy = [name]

        # добавляем статусы домашних (если есть)
        about_guy.extend(spans[1:] if len(spans) > 1 else ["нет данных"])
        students.append(about_guy)

    # сортировка студентов
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
        totals=[''] * (len(students[0]) - 1 if students else 0)
    )
