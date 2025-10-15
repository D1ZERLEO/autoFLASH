def get_homeworks(s: requests.Session, lesson_id):
    import os
    import sys
    import logging
    from urllib.parse import urljoin
    import requests
    from bs4 import BeautifulSoup

    # логгер в stderr
    logger = logging.getLogger("get_api_homeworks")
    if not logger.handlers:
        h = logging.StreamHandler(stream=sys.stderr)
        h.setFormatter(logging.Formatter("%(asctime)s %(levelname)s: %(message)s"))
        logger.addHandler(h)
    logger.setLevel(logging.INFO)

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

    # --- Авторизация ---
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
        password_field = pick(keys, ["password", "pass"]) or "password"

        payload[email_field] = email or ""
        payload[password_field] = pwd or ""

        action = login_form.get("action") or "/login"
        action = urljoin(login_url, action)
        method = (login_form.get("method") or "post").lower()
    else:
        action = f"https://{domain}/login"
        method = "post"
        payload = {"email": email or "", "password": pwd or ""}

    logger.info("Submitting login to %s", action)
    if method == "post":
        login_resp = s.post(action, data=payload, headers={**headers, "Referer": login_url}, timeout=15, allow_redirects=True)
    else:
        login_resp = s.get(action, params=payload, headers={**headers, "Referer": login_url}, timeout=15, allow_redirects=True)

    logger.info("Login final url: %s status: %s", getattr(login_resp, "url", None), getattr(login_resp, "status_code", None))
    logger.debug("Cookies after login: %s", list(s.cookies.keys()))

    # --- Основной запрос ---
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
        logger.warning("Не найден маркер успешной авторизации на student_live/index.")
        logger.warning(resp.text[:800])

    # --- Парсинг со всех страниц ---
    parsed = []
    try:
        max_pages = 10  # если страниц больше — увеличь
        for page_num in range(1, max_pages + 1):
            params["page"] = page_num
            logger.info("Fetching student_live page %d", page_num)
            resp_page = s.get(student_live_url, params=params, headers=headers, timeout=15)
            s2 = BeautifulSoup(resp_page.text, "html.parser")

            tbody = s2.find("tbody", id="student_lives_body")
            if not tbody:
                logger.info("No table body found on page %d, stopping", page_num)
                break

            rows = tbody.find_all("tr")
            if not rows:
                logger.info("No rows found on page %d, stopping", page_num)
                break

            for tr in rows:
                tds = tr.find_all("td")
                if len(tds) < 3:
                    continue
                student_name = tds[2].get_text(strip=True)

                for a in tr.find_all("a", href=True):
                    href = a["href"]
                    if "student_live/tasks" not in href:
                        continue
                    spans = [sp.get_text(strip=True) for sp in a.find_all("span")]
                    b = tr.find("b", attrs={"data-datetime": True})
                    dt = b.get("data-datetime") if b else None
                    parsed.append((student_name, href, spans, dt))

        logger.info("Parsed %d homework links total", len(parsed))

    except Exception as e:
        logger.exception("Ошибка парсинга student_live pages: %s", e)

    # --- Добавляем результат к Response ---
    try:
        setattr(resp, "parsed_homeworks", parsed)
    except Exception:
        logger.exception("Не удалось присвоить parsed_homeworks к Response объекту")

    return resp
