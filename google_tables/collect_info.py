from bs4 import BeautifulSoup
from functools import reduce
from google_tables.to_table import write
from school_website.get_api_homeworks import get_homeworks
import os

# === Список твоей группы ===
GROUP = [
    "Дмитрий Постнов",
    "Никита Морозов",
    "Дима Бесогонов",
    "Полина Сон",
    "Егор Парбузин",
    "Даниил Лучко",
    "Тимур Махмудов",
    "Денис Ганагин",
    "Иван Романов",
    "Дмитрий Нормов",
    "Иван Шиганов",
    "Анастасия Жихарева",
    "арина конвисар",
    "Виктория Ахунова",
    "Софья Шишкина",
    "Тимур Юлдашев",
    "Кирилл Гнусов",
    "Алина Колоскова",
    "Полинка Каширская",
    "Алексей Липский",
    "Роман Гаак",
    "Данила Зорченко",
    "Vlada Kalinskaya",
    "Софа Мартынова",
    "Степан Чугунов",
    "Вероника Горб",
    "Захар .",
    "Egor Averchenkov",
    "Айсёна Светлова",
    "Nikita Ageev",
    "Алла Марущак",
    "Бектагиров Даниял Тагирович",
    "ヴォイシモイ ビラクトット",
    "Валерия Туровская",
    "Фрицлер Виктория Владимировна"
]

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

        # 🔹 Проверяем принадлежность ученика к группе
        if name not in GROUP:
            continue

        about_guy = [name]

        # 🔹 Идём по всем домашкам, начиная с 6-го индекса
        for hmw in items[6:]:
            link = hmw.find("a", href=True)
            if link:
                spans = [sp.get_text(strip=True) for sp in link.find_all("span")]
                if spans:
                    mark = spans[0].split("/")[0]  # 🔹 Берём только число до "/"
                    about_guy.append(mark)
                else:
                    about_guy.append("сдано")
            else:
                span = hmw.find("span")
                if span:
                    about_guy.append(span.get_text(strip=True))
                else:
                    about_guy.append("нет данных")

        students.append(about_guy)

    # сортировка студентов (A-Z сначала латиница)
    students.sort(key=lambda x: (ord('A') <= ord(x[0][0].upper()) <= ord('Z'), x[0]))

    print('Make changes at table...')
    iterator = iter(reduce(lambda x, y: x + y, [k[1:] for k in students]))
    write(
        title=lesson_title,
        deadline=deadline,
        q_students=len(students),
        grades=iterator,
        totals=[''] * (len(students[0]) - 1)
    )
