# вставь вместо старой get_homeworks
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
    # ищем скрытые input'ы: _token, csrf_token и т.п.
    for name in ("_token", "csrf_token", "csrf-token", "csrf"):
        inp = soup.find("input", {"name": name})
        if inp and inp.get("value"):
            return inp["value"]
    # meta
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
    # prefer form containing password input
    for f in soup.find_all("form"):
        if f.find("input", {"type": "password"}):
            login_form = f
            break
    if not login_form:
        # fallback to first form
        forms = soup.find_all("form")
        if forms:
            login_form = forms[0]

    payload = {}
    if login_form:
        # collect all inputs
        for inp in login_form.find_all("input"):
            name = inp.get("name")
            if not name:
                continue
            # default value or empty string
            payload[name] = inp.get("value", "")

        # detect email/password field names heuristically
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

        # action
        action = login_form.get("action") or "/login"
        action = urljoin(login_url, action)
        method = (login_form.get("method") or "post").lower()
    else:
        # no form found: try meta csrf or simple POST
        csrf = _find_csrf(soup)
        payload = {"email": email or "", "password": pwd or ""}
        action = f"https://{domain}/login"
        method = "post"
        if csrf:
            # some apps expect token header
            headers["X-CSRF-TOKEN"] = csrf

    logger.info("Submitting login to %s (method=%s). Email field used: %s", action, method, 'email')
    try:
        if method == "post":
            login_resp = s.post(action, data=payload, headers={**headers, "Referer": login_url}, timeout=15, allow_redirects=True)
        else:
            login_resp = s.get(action, params=payload, headers={**headers, "Referer": login_url}, timeout=15, allow_redirects=True)
    except Exception as e:
        logger.exception("Exception while submitting login: %s", e)
        raise

    logger.info("Login final url: %s status: %s", getattr(login_resp, "url", None), getattr(login_resp, "status_code", None))
    logger.debug("Cookies after login: %s", list(s.cookies.keys()))

    # теперь проверочный запрос на student_live/index
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

    # проверяем наличие маркера выхода (на странице админки есть кнопка Выйти -> https://admin.100points.ru/logout)
    auth_ok = ("Выйти" in resp.text) or ("/logout" in resp.text) or ("student_live/index" in resp.url)
    logger.info("Auth check: %s", auth_ok)
    if not auth_ok:
        # лог для диагностики — первые 800 символов
        logger.warning("Не найден маркер успешной авторизации на student_live/index. Вот начало страницы:")
        logger.warning(resp.text[:800])
        # Не бросаем ошибку автоматически — иногда сайт возвращает админку без текстового 'Выйти'.
        # Если хочешь, можно сделать raise здесь.

    # парсинг ссылок на домашки из <tbody id="student_lives_body">
    parsed = []
    try:
        s2 = BeautifulSoup(resp.text, "html.parser")
        tbody = s2.find("tbody", id="student_lives_body")
        if tbody:
            for a in tbody.find_all("a", href=True):
                href = a["href"]
                if "student_live/tasks" not in href:
                    continue
                spans = [sp.get_text(strip=True) for sp in a.find_all("span")]
                # попытаемся найти дедлайн в родительских td: b[data-datetime]
                parent_td = a.find_parent("td")
                if not parent_td:
                    # возможно дедлайн в соседнем td — ищем ближайший <b data-datetime> в строке
                    tr = a.find_parent("tr")
                    dt = None
                    if tr:
                        b = tr.find("b", attrs={"data-datetime": True})
                        dt = b.get("data-datetime") if b and b.get("data-datetime") else None
                else:
                    b = parent_td.find("b", attrs={"data-datetime": True})
                    dt = b.get("data-datetime") if b and b.get("data-datetime") else None

                parsed.append((href, spans, dt))
    except Exception as e:
        logger.exception("Ошибка парсинга student_live page: %s", e)

    logger.info("Parsed %d homework links", len(parsed))
    # добавляем атрибут parsed_homeworks в объект Response для обратной совместимости
    try:
        setattr(resp, "parsed_homeworks", parsed)
    except Exception:
        logger.exception("Не удалось присвоить parsed_homeworks к Response объекту")
    print(resp)
    return resp
