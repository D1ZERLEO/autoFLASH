import os
from urllib.parse import urljoin
import requests
from bs4 import BeautifulSoup

def get_homeworks(s: requests.Session, lesson_id, verbose: bool = True):
    """
    Авторизуется на https://{API_DOMAIN}/login и возвращает Response страницы student_live/index.
    По-умолчанию печатает диагностику (verbose=True).
    """
    domain = os.getenv("API_DOMAIN")
    if not domain:
        raise RuntimeError("API_DOMAIN environment variable is not set")

    login_url = f"https://{domain}/login"
    headers = {"User-Agent": "Mozilla/5.0"}

    if verbose:
        print("GET login page:", login_url)
    login_page = s.get(login_url, headers=headers)
    if verbose:
        print("login page status:", login_page.status_code)
    soup = BeautifulSoup(login_page.text, "html.parser")

    # --- попытка найти форму логина (предпочтение: форма с полем password) ---
    forms = soup.find_all("form")
    login_form = None
    for f in forms:
        if f.find("input", {"type": "password"}):
            login_form = f
            break
    if not login_form and forms:
        login_form = forms[0]

    # Если форма не найдена — попробуем извлечь csrf из meta и пойти другим путём
    if not login_form:
        # чекнем meta-токен
        meta_csrf = None
        for name in ("csrf-token", "_token", "csrf"):
            m = soup.find("meta", {"name": name})
            if m and m.get("content"):
                meta_csrf = m["content"]
                break
        if verbose:
            print("Warning: login <form> not found on login page. meta_csrf:", bool(meta_csrf))
        # Попробуем POST на /login с полями email/password и (возможно) X-CSRF-TOKEN header
        post_action = f"https://{domain}/login"
        payload = {
            "email": os.getenv("API_ACCOUNT_EMAIL"),
            "password": os.getenv("API_ACCOUNT_PASSWORD"),
        }
        post_headers = headers.copy()
        if meta_csrf:
            post_headers["X-CSRF-TOKEN"] = meta_csrf
        login_resp = s.post(post_action, data=payload, headers=post_headers, allow_redirects=True)
    else:
        # --- собираем все <input> как базу payload ---
        payload = {}
        for inp in login_form.find_all("input"):
            name = inp.get("name")
            if not name:
                continue
            # для чекбоксов/радио учитываем checked
            itype = (inp.get("type") or "").lower()
            if itype in ("checkbox", "radio"):
                if "checked" in inp.attrs:
                    payload[name] = inp.get("value", "on")
                else:
                    # не добавляем неотмеченные
                    continue
            else:
                payload[name] = inp.get("value", "")

        # определяем имена полей для email/login и password
        email_env = os.getenv("API_ACCOUNT_EMAIL")
        pass_env = os.getenv("API_ACCOUNT_PASSWORD")
        if not email_env or not pass_env:
            raise RuntimeError("API_ACCOUNT_EMAIL or API_ACCOUNT_PASSWORD environment variable is empty")

        def find_field_by_keywords(dct_keys, keywords):
            for k in dct_keys:
                lk = k.lower()
                for kw in keywords:
                    if kw in lk:
                        return k
            return None

        email_field = find_field_by_keywords(payload.keys(), ["email", "e-mail", "login", "username", "user"])
        password_field = find_field_by_keywords(payload.keys(), ["password", "pass"])

        # если не нашли по именам — ищем по типу
        if not password_field:
            pwd_inp = login_form.find("input", {"type": "password"})
            if pwd_inp and pwd_inp.get("name"):
                password_field = pwd_inp.get("name")
        if not email_field:
            email_inp = login_form.find("input", {"type": "email"})
            if email_inp and email_inp.get("name"):
                email_field = email_inp.get("name")

        # если всё ещё не нашли — используем общие имена
        if not email_field:
            email_field = "email"
        if not password_field:
            password_field = "password"

        payload[email_field] = email_env
        payload[password_field] = pass_env

        # action и method
        action = login_form.get("action") or "/login"
        action = urljoin(login_url, action)
        method = (login_form.get("method") or "post").lower()

        # заголовки
        post_headers = headers.copy()
        # если форма помечена для ajax
        if login_form.get("data-remote") or login_form.get("data-ajax") or login_form.get("data-async"):
            post_headers["X-Requested-With"] = "XMLHttpRequest"

        # если есть meta csrf-token, добавим в заголовки
        meta_token = None
        for name in ("csrf-token", "_token", "csrf"):
            m = soup.find("meta", {"name": name})
            if m and m.get("content"):
                meta_token = m["content"]
                break
        if meta_token:
            post_headers["X-CSRF-TOKEN"] = meta_token

        if verbose:
            print("Will submit login form:", method.upper(), action)
            print("Detected fields:", list(payload.keys()))
            print("Using email field:", email_field, "password_field:", password_field)
        # отправляем запрос
        if method == "post":
            login_resp = s.post(action, data=payload, headers=post_headers, allow_redirects=True)
        else:
            login_resp = s.get(action, params=payload, headers=post_headers, allow_redirects=True)

    # --- диагностика ответа логина ---
    if verbose:
        print("login response code:", getattr(login_resp, "status_code", None))
        print("login final url:", getattr(login_resp, "url", None))
        # печатаем cookie-короткую сводку
        cookies = {c.name: c.value for c in s.cookies}
        print("session cookies after login (summary):", list(cookies.keys()))

    # простой критерий успешной авторизации — редирект не на /login и наличие ссылки logout / "Выйти" на защищённой странице
    # сделаем проверочный запрос на student_live/index
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
        "module_id": os.getenv("MODULE_ID"),
        "lesson_id": lesson_id,
    }
    check_resp = s.get(student_live_url, params=params, headers=headers)
    if verbose:
        print("check student_live/index status:", check_resp.status_code)
        # небольшой контентный чек: ищем 'Выйти' или '/logout' или 'student_live/index' (страница журнала)
        has_logout = ("Выйти" in check_resp.text) or ("/logout" in check_resp.text) or ("student_live/index" in check_resp.text)
        print("check page contains logout/student_live marker:", has_logout)

    if not has_logout:
        # финальная диагностическая подсказка и ошибка
        if verbose:
            print("Авторизация, похоже, не прошла: на странице student_live/index нет ожидаемых маркеров 'Выйти' или '/logout'.")
            print("-> login response url:", getattr(login_resp, "url", None))
            print("-> login response length:", len(getattr(login_resp, "text", "")))
            # порезанный вывод html для анализа
            print("login response (first 600 chars):")
            print((getattr(login_resp, "text", "") or "")[:600])
            print("student_live/index (first 600 chars):")
            print((getattr(check_resp, "text", "") or "")[:600])
        raise RuntimeError("Авторизация не удалась — см. диагностику в выводе")

    # OK: возвращаем страницу student_live/index (как раньше)
    check_resp.raise_for_status()
    return check_resp
