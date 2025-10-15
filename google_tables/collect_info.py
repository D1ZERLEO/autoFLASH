from bs4 import BeautifulSoup
from functools import reduce

from google_tables.to_table import write
from school_website.get_api_homeworks import get_homeworks

import os

Лёва, [15.10.2025 20:45]
import os
import sys
import time
import logging
from urllib.parse import urljoin
import requests
from bs4 import BeautifulSoup

logger = logging.getLogger("get_api_homeworks")
if not logger.handlers:
    h = logging.StreamHandler(stream=sys.stderr)
    h.setFormatter(logging.Formatter("%(asctime)s %(levelname)s: %(message)s"))
    logger.addHandler(h)
logger.setLevel(logging.INFO)


def _find_csrf(soup):
    for name in ("_token", "csrf_token", "csrf-token", "csrf"):
        inp = soup.find("input", {"name": name})
        if inp and inp.get("value"):
            return inp["value"]
    for name in ("csrf-token", "_token", "csrf"):
        m = soup.find("meta", {"name": name})
        if m and m.get("content"):
            return m["content"]
    return None


def get_homeworks(s: requests.Session, lesson_id):
    print('get_homeworks is working')
    domain = os.getenv("API_DOMAIN")
    if not domain:
        raise RuntimeError("API_DOMAIN is not set")

    email = os.getenv("API_ACCOUNT_EMAIL")
    pwd = os.getenv("API_ACCOUNT_PASSWORD")
    module_id = os.getenv("MODULE_ID")

    logger.info("get_homeworks: domain=%s lesson_id=%s module_id=%s", domain, lesson_id, module_id)

    login_url = f"https://{domain}/login"
    headers = {"User-Agent": "Mozilla/5.0"}

    logger.info("GET %s", login_url)
    login_page = s.get(login_url, headers=headers, timeout=15)
    soup = BeautifulSoup(login_page.text, "html.parser")

    # ищем форму входа
    login_form = None
    for f in soup.find_all("form"):
        if f.find("input", {"type": "password"}):
            login_form = f
            break
    if not login_form:
        forms = soup.find_all("form")
        if forms:
            login_form = forms[0]

    payload = {}
    if login_form:
        for inp in login_form.find_all("input"):
            name = inp.get("name")
            if not name:
                continue
            payload[name] = inp.get("value", "")

        keys = list(payload.keys())

        def pick(keys, candidates):
            for k in keys:
                lk = k.lower()
                for c in candidates:
                    if c in lk:
                        return k
            return None

        email_field = pick(keys, ["email", "e-mail", "login", "user", "username"]) or "email"
        password_field = pick(keys, ["password", "pass"]) or None
        if not password_field:
            pwd_input = login_form.find("input", {"type": "password"})
            if pwd_input and pwd_input.get("name"):
                password_field = pwd_input.get("name")
        if not password_field:
            password_field = "password"

        payload[email_field] = email or ""
        payload[password_field] = pwd or ""

        action = login_form.get("action") or "/login"
        action = urljoin(login_url, action)
        method = (login_form.get("method") or "post").lower()
    else:
        csrf = _find_csrf(soup)
        payload = {"email": email or "", "password": pwd or ""}
        action = f"https://{domain}/login"
        method = "post"
        if csrf:
            headers["X-CSRF-TOKEN"] = csrf

    logger.info("Submitting login to %s (method=%s)", action, method)
    if method == "post":
        login_resp = s.post(action, data=payload, headers={**headers, "Referer": login_url}, timeout=15)
    else:
        login_resp = s.get(action, params=payload, headers={**headers, "Referer": login_url}, timeout=15)

    logger.info("Login final url: %s status: %s", getattr(login_resp, "url", None), getattr(login_resp, "status_code", None))

    student_live_url = f"https://{domain}/student_live/index"
    params = {
        "email": "",
        "full_name": "",
        "hidden_last_name": "",
        "hidden_first_name": "",
        "hidden_mid_name": "",
        "vk_id": "",
        "subject_id": "20",
        "course_id": "1856",
        "module_id": module_id,
        "lesson_id": lesson_id,
    }

    parsed = []

    # -----------------------------
    # 🔹 вот тут фильтрация по именам
    # -----------------------------
    target_names = [

Лёва, [15.10.2025 20:45]
"Дмитрий Постнов", "Никита Морозов", "Дима Бесогонов", "Полина Сон", "Егор Парбузин",
        "Даниил Лучко", "Тимур Махмудов", "Денис Ганагин", "Иван Романов", "Дмитрий Нормов",
        "Иван Шиганов", "Анастасия Жихарева", "Арина Конвисар", "Виктория Ноубрейн",
        "Софья Шишкина", "Тимур Юлдашев", "Ученик", "Алина Колоскова", "Полинка Каширская",
        "Алексей Липский", "Гаак Роман Витальевич", "Зорченко Данила Сергеевич",
        "Vlada Kalinskaya", "Софа Мартынова", "Степан Чугунов", "Горб Вероника Александровна",
        "Шуйская Ирина Вячеславовна", "Egor Averchenkov", "Айсари Светлова", "Nikita Ageev",
        "Алла Марущак", "Бектагиров Даниял Тагирович", "ヴォイシモイ ビラクトット", "Валерия Туровская"
    ]

    for name in target_names:
        params["full_name"] = name
        logger.info("Fetching student_live for %s", name)
        resp_one = s.get(student_live_url, params=params, headers=headers, timeout=15)
        s2 = BeautifulSoup(resp_one.text, "html.parser")
        tbody = s2.find("tbody", id="student_lives_body")
        if not tbody:
            continue

        for tr in tbody.find_all("tr"):
            tds = tr.find_all("td")
            if len(tds) < 3:
                continue
            student_name = tds[2].get_text(strip=True)
            if student_name != name:
                continue

            for a in tr.find_all("a", href=True):
                href = a["href"]
                if "student_live/tasks" not in href:
                    continue
                spans = [sp.get_text(strip=True) for sp in a.find_all("span")]
                b = tr.find("b", attrs={"data-datetime": True})
                dt = b.get("data-datetime") if b else None
                parsed.append((href, spans, dt))

        time.sleep(0.3)  # пауза между запросами, чтобы не заддосить

    # -----------------------------
    logger.info("Parsed %d homework links", len(parsed))
    try:
        setattr(resp_one, "parsed_homeworks", parsed)
    except Exception:
        logger.exception("Не удалось присвоить parsed_homeworks к Response объекту")

    return resp_one


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
