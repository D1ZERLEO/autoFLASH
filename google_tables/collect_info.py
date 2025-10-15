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
            link = hmw.find("a", href=True)
            if link:
                spans = [sp.get_text(strip=True) for sp in link.find_all("span")]
                if spans:
                    raw = spans[0]
    
                    # 🧠 Берём только первое число из "6/7", "86%", "50 / 100", и т.п.
                    import re
                    m = re.search(r"\d+", raw)
                    about_guy.append(m.group(0) if m else "0")
                else:
                    about_guy.append("0")
            else:
                span = hmw.find("span")
                if span:
                    raw = span.get_text(strip=True)
                    import re
                    m = re.search(r"\d+", raw)
                    about_guy.append(m.group(0) if m else "0")
                else:
                    about_guy.append("0")
    
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
