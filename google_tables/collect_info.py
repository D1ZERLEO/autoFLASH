def write_lesson_homework(s, lesson_id, lesson_title, deadline):
    import re
    import os
    from functools import reduce
    from bs4 import BeautifulSoup
    from google_tables.to_table import write
 

    print(f"--- Сбор данных по уроку {lesson_title} ---")
    TARGET_NAMES = [


        "Дмитрий Постнов", "Никита Морозов", "Дима Бесогонов", "Полина Сон", "Егор Парбузин",
        "Даниил Лучко", "Тимур Махмудов", "Денис Ганагин", "Иван Романов", "Дмитрий Нормов",
        "Иван Шиганов", "Анастасия Жихарева", "арина конвисар", "Виктория Ахунова",
        "Софья Шишкина", "Тимур Юлдашев", "Кирилл Гнусов", "Алина Колоскова", "Полинка Каширская",
        "Алексей Липский", "Гаак Роман Витальевич", "Зорченко Данила Сергеевич",
        "Vlada Kalinskaya", "Софа Мартынова", "Степан Чугунов", "Горб Вероника Александровна",
        "Шуйская Ирина Вячеславовна", "Egor Averchenkov", "Айсёна Светлова", "Nikita Ageev",
        "Алла Марущак", "Бектагиров Даниял Тагирович", "ヴォイシモイ ビラクトット", "Валерия Туровская","Вика Фрицлер"
    ]
    # Получаем страницу и все домашки
    page = get_homeworks(s, lesson_id)
    all_data = getattr(page, "parsed_homeworks", [])
    print(f"Всего найдено домашних по всем страницам: {len(all_data)}")

    # Фильтруем — оставляем только моих учеников
    filtered = [p for p in all_data if p[0] in TARGET_NAMES]
    print(f"Из них моих учеников: {len(filtered)}")

    # Если по какой-то причине parsed_homeworks пуст — fallback на HTML
    if not filtered:
        print("⚠️ Не найдено ни одного совпадения по именам — пробуем парсить HTML напрямую")
        soup = BeautifulSoup(page.text, "html.parser")
        tbody = soup.find("tbody", id="student_lives_body")
        if tbody:
            for tr in tbody.find_all("tr"):
                tds = tr.find_all("td")
                if len(tds) < 3:
                    continue
                student_name = tds[2].get_text(strip=True)
                if student_name in TARGET_NAMES:
                    spans = [sp.get_text(strip=True) for sp in tr.find_all("span")]
                    filtered.append((student_name, None, spans, None))
        print(f"После HTML fallback найдено: {len(filtered)}")

    print("Формируем таблицу...")

    # Преобразуем данные: извлекаем только числа (например 6 из "6/7" или "86%")
    students = []
    for student_name, href, spans, dt in filtered:
        about = [student_name]
        if spans:
            # Берём все span и вычленяем только числа
            for sp in spans:
                m = re.search(r"\d+", sp)
                about.append(m.group(0) if m else "0")
        else:
            about.append("0")
        students.append(about)

    # Добавляем отсутствующих (у кого нет данных)
    found_names = {s[0] for s in students}
    for name in TARGET_NAMES:
        if name not in found_names:
            students.append([name, "нет данных"])

    # Сортируем для стабильности
    students.sort(key=lambda x: x[0])

    print(f"Готово. В таблице будет {len(students)} строк.")

    # Подготавливаем данные для записи
    if students:
        iterator = iter(reduce(lambda x, y: x + y, [k[1:] for k in students]))
        totals_len = len(students[0]) - 1
    else:
        iterator = iter([])
        totals_len = 0

    # Записываем в Google таблицу
    write(
        title=lesson_title,
        deadline=deadline,
        q_students=len(students),
        grades=iterator,
        totals=[''] * totals_len
    )

    print(f"✅ Таблица успешно обновлена: {lesson_title} ({len(students)} учеников)")
