# file: get_api_homeworks.py
import os
import sys
import logging
from urllib.parse import urljoin
import requests
from bs4 import BeautifulSoup

# логгер -> stderr (чтобы CI/runner не скрывал вывод)
logger = logging.getLogger(__name__)
if not logger.handlers:
    h = logging.StreamHandler(stream=sys.stderr)
    h.setFormatter(logging.Formatter("%(asctime)s %(levelname)s: %(message)s"))
    logger.addHandler(h)
logger.setLevel(logging.DEBUG)

# явный маркер загрузки модуля
logger.debug("LOADED MODULE get_api_homeworks (%s)", __file__)

def get_homeworks(s: requests.Session, lesson_id):
    """
    Авторизация + запрос student_live/index.
    Возвращает requests.Response (как раньше). Также к response будет добавлено поле parsed_homeworks.
    Очень подробный лог для отладки.
    """
    logger.info("ENTER get_homeworks(lesson_id=%s)", lesson_id)

    domain = os.getenv("API_DOMAIN")
    email = os.getenv("API_ACCOUNT_EMAIL")
    pwd = os.getenv("API_ACCOUNT_PASSWORD")
    module_id = os.getenv("MODULE_ID")

    logger.debug("ENV: API_DOMAIN=%s, API_ACCOUNT_EMAIL=%s, MODULE_ID=%s",
                 domain or "<MISSING>", (email[:4] + "..." if email else "<MISSING>"), module_id or "<MISSING>")

    if not domain:
        raise RuntimeError("API_DOMAIN environment variable is not set")

    login_url = f"https://{domain}/login"
    headers = {"User-Agent": "Mozilla/5.0"}

    logger.info("GET login page: %s", login_url)
    login_page = s.get(login_url, headers=headers, timeout=15)
    logger.info("login page status: %s", login_page.status_code)

    soup = BeautifulSoup(login_page.text, "html.parser")
    forms = soup.find_all("form")
    logger.debug("Found %d <form> on login page", len(forms))

    # ищем форму с полем password
    login_form = None
    for f in forms:
        if f.find("input", {"type": "password"}):
            login_form = f
            break
    if not login_form and forms:
        login_form = forms[0]

    if not login_form:
        logger.error("NO login <form> found. Dumping first 800 chars of login page for diagnosis:")
        logger.error(login_page.text[:800])
        raise RuntimeError("Не найдена форма логина на странице " + login_url)

    # собираем все input'ы
    payload = {}
    for inp in login_form.find_all("input"):
        name = inp.get("name")
        if not name:
            continue
        # по умолчанию берем value или пустую строку
        payload[name] = inp.get("value", "")

    logger.debug("Form input names (%d): %s", len(payload), list(payload.keys())[:30])

    # эвристика: определяем поля email/password
    def pick_field(keys, keywords):
        for k in keys:
            lk = k.lower()
            for kw in keywords:
                if kw in lk:
                    return k
        return None

    email_field = pick_field(payload.keys(), ["email", "e-mail", "login", "user", "username"]) or "email"
    password_field = pick_field(payload.keys(), ["password", "pass"]) 
    if not password_field:
        pwd_input = login_form.find("input", {"type": "password"})
        if pwd_input and pwd_input.get("name"):
            password_field = pwd_input.get("name")
    if not password_field:
        password_field = "password"

    # вставляем реальные креды (если есть)
    if email is None or pwd is None:
        logger.warning("API_ACCOUNT_EMAIL or API_ACCOUNT_PASSWORD is not set (one or both missing). Will still attempt request.")
    payload[email_field] = email or ""
    payload[password_field] = pwd or ""

    # вычисляем action
    action = login_form.get("action") or "/login"
    action = urljoin(login_url, action)
    method = (login_form.get("method") or "post").lower()

    logger.info("Submitting login form -> %s (method=%s)", action, method)
    logger.debug("Using fields: email_field=%s password_field=%s", email_field, password_field)
    logger.debug("Payload keys sample: %s", list(payload.keys())[:40])

    # POST/GET в зависимости от метода
    try:
        if method == "post":
            login_resp = s.post(action, data=payload, headers={**headers, "Referer": login_url}, timeout=15, allow_redirects=True)
        else:
            login_resp = s.get(action, params=payload, headers={**headers, "Referer": login_url}, timeout=15, allow_redirects=True)
    except Exception as e:
        logger.exception("Exception while submitting login form: %s", e)
        raise

    logger.info("Login response status: %s final_url: %s", getattr(login_resp, "status_code", None), getattr(login_resp, "url", None))
    logger.debug("Session cookies after login: %s", list(s.cookies.keys()))

    # Проверочный запрос на student_live/index
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
    logger.info("GET %s with lesson_id=%s", student_live_url, lesson_id)
    student_resp = s.get(student_live_url, params=params, headers=headers, timeout=15)
    logger.info("student_live status=%s url=%s", student_resp.status_code, student_resp.url)

    # Контрольный маркер успешной авторизации
    logged_marker = ("Выйти" in student_resp.text) or ("/logout" in student_resp.text) or ("student_live/index" in student_resp.text)
    logger.info("Auth marker found on page (Выйти or /logout): %s", logged_marker)
    if not logged_marker:
        logger.warning("Не обнаружен маркер успешной авторизации на странице student_live/index. Dumping first 1000 chars:")
        logger.warning(student_resp.text[:1000])
        # НЕ бросаем исключение — даём вызвать дальше, caller увидит dump в логах

    # Парсим ссылки на домашки и добавляем к response
    parsed = []
    try:
        soup2 = BeautifulSoup(student_resp.text, "html.parser")
        tbody = soup2.find("tbody", id="student_lives_body")
        if tbody:
            for a in tbody.find_all("a", href=True):
                href = a["href"]
                if "student_live/tasks" in href:
                    spans = [sp.get_text(strip=True) for sp in a.find_all("span")]
                    parsed.append((href, spans))
    except Exception:
        logger.exception("Ошибка при парсинге student_live page")

    logger.info("Parsed %d homework links from page", len(parsed))
    # прикрепляем поле к response (обратно-совместимо — функция по-прежнему возвращает Response)
    try:
        setattr(student_resp, "parsed_homeworks", parsed)
    except Exception:
        logger.exception("Не удалось присвоить parsed_homeworks к Response объекту")

    return student_resp
