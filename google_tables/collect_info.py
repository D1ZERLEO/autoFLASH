from bs4 import BeautifulSoup
from functools import reduce

from google_tables.to_table import write
from school_website.get_api_homeworks import get_homeworks

import os

def write_lesson_homework(s, lesson_id, lesson_title, deadline):
    import re
    import os
    from functools import reduce
    from bs4 import BeautifulSoup
    from google_tables.to_table import write

    # Получаем данные с сайта
    page = get_homeworks(s, lesson_id)
    print(f'Made all of the requests to the {os.getenv("API_DOMAIN")}!')

    # Берём готовые данные из get_homeworks
    parsed_homeworks = getattr(page, "parsed_homeworks", [])
    print(f'Всего найдено домашних: {len(parsed_homeworks)}')

    # Если parsed_homeworks пуст, fallback на HTML (для отладки)
    if not parsed_homeworks:
        print("⚠️ parsed_homeworks пуст — fallback к HTML-парсеру")
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

    # Список целевых имён (всех учеников)
    target_names = [


        "Дмитрий Постнов", "Никита Морозов", "Дима Бесогонов", "Полина Сон", "Егор Парбузин",
        "Даниил Лучко", "Тимур Махмудов", "Денис Ганагин", "Иван Романов", "Дмитрий Нормов",
        "Иван Шиганов", "Анастасия Жихарева", "арина конвисар", "Виктория Ахунова",
        "Софья Шишкина", "Тимур Юлдашев", "Кирилл Гнусов", "Алина Колоскова", "Полинка Каширская",
        "Алексей Липский", "Гаак Роман Витальевич", "Зорченко Данила Сергеевич",
        "Vlada Kalinskaya", "Софа Мартынова", "Степан Чугунов", "Горб Вероника Александровна",
        "Шуйская Ирина Вячеславовна", "Egor Averchenkov", "Айсёна Светлова", "Nikita Ageev",
        "Алла Марущак", "Бектагиров Даниял Тагирович", "ヴォイシモイ ビラクトット", "Валерия Туровская","Вика Фрицлер"
    ]

    print('Collect information about students...')
    students = []

    # --- Основная логика извлечения ---
    soup = BeautifulSoup(page.text, "html.parser")
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
                    m = re.search(r"\d+", raw)
                    about_guy.append(m.group(0) if m else "0")
                else:
                    about_guy.append("0")
            else:
                span = hmw.find("span")
                if span:
                    raw = span.get_text(strip=True)
                    m = re.search(r"\d+", raw)
                    about_guy.append(m.group(0) if m else "0")
                else:
                    about_guy.append("0")

        students.append(about_guy)

    # --- Добавляем отсутствующих учеников (без данных) ---
    found_names = {s[0] for s in students}
    for name in target_names:
        if name not in found_names:
            students.append([name, "нет данных"])

    # --- Сортировка для стабильности ---
    students.sort(key=lambda x: (ord('A') <= ord(x[0][0].upper()) <= ord('Z'), x[0]))

    print('Make changes at table...')
    if students:
        iterator = iter(reduce(lambda x, y: x + y, [k[1:] for k in students]))
        totals_len = len(students[0]) - 1
    else:
        iterator = iter([])
        totals_len = 0

    # --- Запись в таблицу ---
    write(
        title=lesson_title,
        deadline=deadline,
        q_students=len(students),
        grades=iterator,
        totals=[''] * totals_len
    )
    print(f"✅ Таблица обновлена: {len(students)} строк, {totals_len} колонок данных.")
