import os
import sys
import logging
from urllib.parse import urljoin
import time
import random
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
    print("get_homeworks is working")

    domain = os.getenv("API_DOMAIN")
    if not domain:
        raise RuntimeError("API_DOMAIN is not set")

    email = os.getenv("API_ACCOUNT_EMAIL")
    pwd = os.getenv("API_ACCOUNT_PASSWORD")
    module_id = os.getenv("MODULE_ID")

    logger.info("get_homeworks: domain=%s lesson_id=%s module_id=%s",
                domain, lesson_id, module_id)

    # --- Браузерные заголовки (иначе капча!) ---
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:129.0) Gecko/20100101 Firefox/129.0",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "ru,en;q=0.5",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive",
        "DNT": "1",
        "Upgrade-Insecure-Requests": "1",
    }

    # =============================== LOGIN ======================================
    login_url = f"https://{domain}/login"
    logger.info("GET %s", login_url)
    login_page = s.get(login_url, headers=headers, timeout=15)

    soup = BeautifulSoup(login_page.text, "html.parser")
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
            if name:
                payload[name] = inp.get("value", "")

        keys = list(payload.keys())

        def pick(keys, candidates):
            for k in keys:
                lk = k.lower()
                for c in candidates:
                    if c in lk:
                        return k
            return None

        email_field = pick(keys, ["email", "login", "user", "username"]) or "email"
        password_field = pick(keys, ["password", "pass"]) or "password"

        payload[email_field] = email
        payload[password_field] = pwd

        action = urljoin(login_url, login_form.get("action") or "/login")
        method = (login_form.get("method") or "post").lower()

    else:
        csrf = _find_csrf(soup)
        payload = {"email": email, "password": pwd}
        action = login_url
        method = "post"
        if csrf:
            headers["X-CSRF-TOKEN"] = csrf

    try:
        if method == "post":
            login_resp = s.post(action, data=payload, headers=headers,
                                timeout=15, allow_redirects=True)
        else:
            login_resp = s.get(action, params=payload, headers=headers,
                               timeout=15, allow_redirects=True)
    except Exception as e:
        logger.exception("Exception while login: %s", e)
        raise

    logger.info("Login final url: %s status: %s",
                getattr(login_resp, "url", None),
                getattr(login_resp, "status_code", None))

    # =============================== FETCH MAIN PAGE =============================
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

    resp = s.get(student_live_url, params=params, headers=headers, timeout=15)

    # CAPCHA DETECT
    if "captcha" in resp.text.lower() or "робот" in resp.text.lower():
        logger.error("❌ CAPTCHA DETECTED — сайт требует проверку!")
        print(resp.text[:500])
        setattr(resp, "parsed_homeworks", [])
        return resp

    # =============================== PAGINATION =================================
    parsed = []

    def parse_page(html):
        soup = BeautifulSoup(html, "html.parser")
        tbody = soup.find("tbody", id="student_lives_body")
        if not tbody:
            return []

        data = []
        for tr in tbody.find_all("tr"):
            tds = tr.find_all("td")
            if len(tds) < 3:
                continue

            for a in tr.find_all("a", href=True):
                href = a["href"]
                if "student_live/tasks" not in href:
                    continue

                spans = [sp.get_text(strip=True) for sp in a.find_all("span")]

                b = tr.find("b", attrs={"data-datetime": True})
                dt = b.get("data-datetime") if b else None

                data.append((href, spans, dt))

        return data

    html = resp.text
    parsed.extend(parse_page(html))

    # Пагинация
    page_num = 1
    while True:
        soup = BeautifulSoup(html, "html.parser")

        pagination = soup.find("ul", class_="pagination")
        next_link = None
        if pagination:
            for a in pagination.find_all("a", href=True):
                if f"page={page_num+1}" in a["href"]:
                    next_link = urljoin(student_live_url, a["href"])
                    break

        if not next_link:
            break

        time.sleep(random.uniform(0.5, 1.1))
        next_resp = s.get(next_link, headers=headers, timeout=15)
        html = next_resp.text

        parsed.extend(parse_page(html))
        page_num += 1

    logger.info("Parsed %d homework links", len(parsed))

    setattr(resp, "parsed_homeworks", parsed)
    return resp
