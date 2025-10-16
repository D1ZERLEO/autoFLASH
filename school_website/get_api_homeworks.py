import os
import sys
import logging
from urllib.parse import urljoin, urlencode
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
    email = os.getenv("API_ACCOUNT_EMAIL")
    pwd = os.getenv("API_ACCOUNT_PASSWORD")
    module_id = os.getenv("MODULE_ID")

    if not domain:
        raise RuntimeError("API_DOMAIN is not set")

    login_url = f"https://{domain}/login"
    headers = {"User-Agent": "Mozilla/5.0"}

    # === Авторизация ===
    login_page = s.get(login_url, headers=headers, timeout=15)
    soup = BeautifulSoup(login_page.text, "html.parser")

    payload = {"email": email, "password": pwd}
    csrf = _find_csrf(soup)
    if csrf:
        headers["X-CSRF-TOKEN"] = csrf

    logger.info("Авторизация на %s", login_url)
    s.post(login_url, data=payload, headers=headers, timeout=15)

    # === Первый запрос к журналу ===
    student_live_url = f"https://{domain}/student_live/index"
    base_params = {
        "email": "",
        "full_name": "",
        "subject_id": "20",
        "course_id": "1856",
        "module_id": module_id,
        "lesson_id": lesson_id,
    }

    def get_page(page_num: int):
        params = base_params.copy()
        params["page"] = page_num
        url = f"{student_live_url}?{urlencode(params)}"
        logger.info(f"GET {url}")
        resp = s.get(url, headers={**headers, "Referer": student_live_url}, timeout=15)
        logger.info(f"Page {page_num} status {resp.status_code}")
        return resp

    page_num = 1
    pages_html = []

    while True:
        resp = get_page(page_num)
        if resp.status_code != 200:
            break

        soup = BeautifulSoup(resp.text, "html.parser")
        tbody = soup.find("tbody", id="student_lives_body")
        if not tbody:
            logger.warning(f"tbody не найден на странице {page_num}")
            break

        pages_html.append(resp.text)

        # ищем ссылку на следующую страницу
        pagination = soup.find("ul", class_="pagination")
        next_link = pagination.find("a", string=str(page_num + 1)) if pagination else None
        if not next_link:
            logger.info(f"Нет следующей страницы (остановка на {page_num})")
            break

        page_num += 1

    parsed = []
    for i, html in enumerate(pages_html, start=1):
        s2 = BeautifulSoup(html, "html.parser")
        tbody = s2.find("tbody", id="student_lives_body")
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

    logger.info(f"Parsed {len(parsed)} homework links (со всех страниц)")
    try:
        setattr(resp, "parsed_homeworks", parsed)
    except Exception:
        logger.exception("Не удалось присвоить parsed_homeworks к Response объекту")

    return resp
