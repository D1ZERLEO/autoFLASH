import os
import sys
import logging
from urllib.parse import urljoin
import requests
from bs4 import BeautifulSoup

# логгер в stderr — чтобы вывод всегда был виден
logger = logging.getLogger("get_api_homeworks")
if not logger.handlers:
    h = logging.StreamHandler(stream=sys.stderr)
    h.setFormatter(logging.Formatter("%(asctime)s %(levelname)s: %(message)s"))
    logger.addHandler(h)
logger.setLevel(logging.INFO)


def _find_csrf(soup):
    """Ищем csrf-токен в форме или метатегах."""
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
    """
    Авторизуется на https://{API_DOMAIN}/login и возвращает Response страницы student_live/index.
    Response дополнительно содержит attribute parsed_homeworks — list of (href, spans_list, deadline_iso_or_None).
    """
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
    logger.info("login page status: %s", login_page.status_code)

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
            if not name:
                continue
            payload[name] = inp.get("value", "")

        def pick(keys, candidates):
            for k in keys:
                lk = k.lower()
                for c in candidates:
                    if c in lk:
                        return k
            return None

        keys = list(payload.keys())
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

    logger.info("Submitting login to %s (method=%s). Email field used: %s", action, method, 'email')
    try:
        if method == "post":
            login_resp = s.post(action, data=payload, headers={**headers, "Referer": login_url},
                                timeout=15, allow_redirects=True)
        else:
            login_resp = s.get(action, params=payload, headers={**headers, "Referer": login_url},
                               timeout=15, allow_redirects=True)
    except Exception as e:
        logger.exception("Exception while submitting login: %s", e)
        raise

    logger.info("Login final url: %s status: %s", getattr(login_resp, "url", None),
                getattr(login_resp, "status_code", None))
    logger.debug("Cookies after login: %s", list(s.cookies.keys()))

    # Запрашиваем student_live/index
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
    logger.info("GET %s with params lesson_id=%s", student_live_url, lesson_id)
    resp = s.get(student_live_url, params=params, headers=headers, timeout=15)
    logger.info("student_live returned %s %s", resp.status_code, resp.url)

    auth_ok = ("Выйти" in resp.text) or ("/logout" in resp.text) or ("student_live/index" in resp.url)
    logger.info("Auth check: %s", auth_ok)
    if not auth_ok:
        logger.warning("Не найден маркер успешной авторизации на student_live/index. Вот начало страницы:")
        logger.warning(resp.text[:800])

    # === ПАГИНАЦИЯ: парсим все страницы ===
    parsed = []
    try:
        s2 = BeautifulSoup(resp.text, "html.parser")
        page_num = 1

        while True:
            logger.info(f"Парсим страницу {page_num}...")
            tbody = s2.find("tbody", id="student_lives_body")
            if not tbody:
                logger.warning(f"Не найден tbody на странице {page_num}")
                break

            for a in tbody.find_all("a", href=True):
                href = a["href"]
                if "student_live/tasks" not in href:
                    continue
                spans = [sp.get_text(strip=True) for sp in a.find_all("span")]
                parent_td = a.find_parent("td")
                dt = None
                if not parent_td:
                    tr = a.find_parent("tr")
                    if tr:
                        b = tr.find("b", attrs={"data-datetime": True})
                        dt = b.get("data-datetime") if b and b.get("data-datetime") else None
                else:
                    b = parent_td.find("b", attrs={"data-datetime": True})
                    dt = b.get("data-datetime") if b and b.get("data-datetime") else None

                parsed.append((href, spans, dt))

            # ищем ссылку на следующую страницу
            pagination = s2.find("ul", class_="pagination")
            next_link = None
            if pagination:
                for li in pagination.find_all("a", href=True):
                    if "page=" in li["href"] and li.get_text(strip=True) in [str(page_num + 1), "Следующая", ">"]:
                        next_link = li["href"]
                        break

            if not next_link:
                break

            next_url = urljoin(student_live_url, next_link)
            page_num += 1
            logger.info(f"Загружаем {next_url}")
            next_resp = s.get(next_url, headers=headers, timeout=15)
            s2 = BeautifulSoup(next_resp.text, "html.parser")

    except Exception as e:
        logger.exception("Ошибка парсинга student_live page: %s", e)

    logger.info("Parsed %d homework links (включая все страницы)", len(parsed))

    try:
        setattr(resp, "parsed_homeworks", parsed)
    except Exception:
        logger.exception("Не удалось присвоить parsed_homeworks к Response объекту")

    return resp
