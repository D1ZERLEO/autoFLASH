from bs4 import BeautifulSoup
from functools import reduce
from google_tables.to_table import write
from school_website.get_api_homeworks import get_homeworks
import os

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
    "Фрицлер Виктория Владимировна",
    "Влад Климан",
    "Дарья Трофимова",
    "Лиза Дуброва",
    "Ксюша Минина",
    "Чистяков Андрей Максимович",
    "Фомин Антон Викторович",
    "Вероника Иванова",
    "Ксения Халанская",
    "Алина Кожанова",
    "Yesterday Morning",
    "Дмитрий Химич",
    "Елизавета Голдобина",
    "Лутовина Алина Евгеньевна",
    "Марьяна Головкина",
    "Helsas Helsas",
    "Вероника Смагина",
    "Денис Будко",
    "Полина Оглоблина",
    "Елизавета Уросова",
    "Илья Ершов",
    "Кузнецова Ольга Андреевна",
    "Виталик Гуденко",
    "Анна Русова",
    "Елизавета Увина",
    "Fake Emotion",
    "Дамир",
    "Шишов Савелий Павлович",
    "Арина Ахмонен",
    "Дима Ивлев",
    "Настя Игошина",
    "Дарья Комарова",
    "Татьянченко Мария Андреевна",
    "Шумихина Ксения Дмитриевна"
]


def write_lesson_homework(s, lesson_id, lesson_title, deadline):
    page = get_homeworks(s, lesson_id)
    soup = BeautifulSoup(page.text, "html.parser")

    print(f"Made all of the requests to the {os.getenv('API_DOMAIN')}!")
    print("Collect information about students...")

    students = []
    matched = 0
    total = 0

    for row in soup.findAll("tr", class_="odd"):
        items = row.findAll("td")
        if len(items) < 7:
            continue

        name = items[2].get_text(strip=True)
        total += 1

        # Сравниваем без учёта регистра
        if not any(name.lower() == g.lower() for g in GROUP):
            print(f"❌ Пропущен: {name}")
            continue

        print(f"✅ Найден в группе: {name}")
        matched += 1

        about_guy = [name]

        # идём по всем домашкам начиная с 6-го столбца
        for hmw in items[6:]:
            link = hmw.find("a", href=True)
            if link:
                spans = [sp.get_text(strip=True) for sp in link.find_all("span")]
                if spans:
                    mark = spans[0].split("/")[0]  # только число до "/"
                    about_guy.append(mark)
                else:
                    about_guy.append("сдано")
            else:
                span = hmw.find("span")
                about_guy.append(span.get_text(strip=True) if span else "нет данных")

        students.append(about_guy)

    print(f"Всего строк на странице: {total}, совпало по группе: {matched}")

    # сортировка студентов (A-Z — латиница вперёд)
    students.sort(key=lambda x: (ord('A') <= ord(x[0][0].upper()) <= ord('Z'), x[0]))

    print("Make changes at table...")
    iterator = iter(reduce(lambda x, y: x + y, [k[1:] for k in students]))
    write(
        title=lesson_title,
        deadline=deadline,
        q_students=len(students),
        grades=iterator,
        totals=[''] * (len(students[0]) - 1)
    )
