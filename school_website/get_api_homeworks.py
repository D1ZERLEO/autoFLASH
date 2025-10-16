import os
import sys
import logging
from urllib.parse import urljoin, urlencode
import requests
from bs4 import BeautifulSoup

# логгер
logger = logging.getLogger("get_api_homeworks")
if not logger.handlers:
    h = logging.StreamHandler(stream=sys.stderr)
    h.setFormatter(logging.Formatter("%(asctime)s %(levelname)s: %(message)s"))
    logger.addHandler(h)
logger.setLevel(logging.INFO)


def _find_csrf(soup):
    """Ищем csrf-токен."""
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

    # === 1. Авторизация ===
    logger.info("GET %s", login_url)
    login_page = s.get(login_url, headers=headers, timeout=15)
    soup = BeautifulSoup(login_page.text, "html.parser")

    payload = {}
    form = soup.find("form")
    if form:
        for inp in form.find_all("input"):
            if inp.get("name"):
                payload[inp["name"]] = inp.get("value", "")

    payload["email"] = email
    payload["password"] = pwd
    csrf = _find_csrf(soup)
    if csrf:
        headers["X-CSRF-TOKEN"] = csrf

    logger.info("Авторизация на %s", login_url)
    s.post(login_url, data=payload, headers=headers, timeout=15)

    # === 2. Запрашиваем журнал ===
    student_live_url = f"https://{domain}/student_live/index"
    base_params = {
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

    logger.info("GET %s", student_live_url)
    resp = s.get(student_live_url, params=base_params, headers=headers, timeout=15)
    all_rows_html = [resp.text]  # первая страница

    # === 3. Переходим по страницам ===
    page_num = 1
    while True:
        soup = BeautifulSoup(all_rows_html[-1], "html.parser")
        pagination = soup.find("ul", class_="pagination")
        next_link = None

        if pagination:
            for a in pagination.find_all("a", href=True):
                if "page=" in a["href"] and a.get_text(strip=True) in [str(page_num + 1), "Следующая", ">"]:
                    next_link = a["href"]
                    break

        if not next_link:
            logger.info("Нет следующей страницы (остановка на %d)", page_num)
            break

        next_url = urljoin(student_live_url, next_link)
        logger.info(f"Загружаем страницу {page_num + 1}: {next_url}")

        # Если next_link не содержит lesson_id — добавим вручную
        if "lesson_id" not in next_link:
            params = base_params.copy()
            params["page"] = page_num + 1
            next_url = f"{student_live_url}?{urlencode(params)}"

        next_resp = s.get(next_url, headers=headers, timeout=15)
        if next_resp.status_code != 200:
            logger.warning(f"Не удалось загрузить страницу {page_num + 1}: {next_resp.status_code}")
            break

        all_rows_html.append(next_resp.text)
        page_num += 1

    # === 4. Объединяем всех учеников со всех страниц ===
    parsed = []
    for i, html in enumerate(all_rows_html, start=1):
        s2 = BeautifulSoup(html, "html.parser")
        tbody = s2.find("tbody", id="student_lives_body")
        if not tbody:
            logger.warning(f"tbody не найден на странице {i}")
            continue

        for a in tbody.find_all("a", href=True):
            href = a["href"]
            if "student_live/tasks" not in href:
                continue
            spans = [sp.get_text(strip=True) for sp in a.find_all("span")]

            parent_td = a.find_parent("td")
            dt = None
            if parent_td:
                b = parent_td.find("b", attrs={"data-datetime": True})
                dt = b.get("data-datetime") if b and b.get("data-datetime") else None
            parsed.append((href, spans, dt))

    logger.info("Parsed %d homework links (со всех страниц)", len(parsed))

    try:
        setattr(resp, "parsed_homeworks", parsed)
    except Exception:
        logger.exception("Не удалось присвоить parsed_homeworks к Response объекту")

    return resp
