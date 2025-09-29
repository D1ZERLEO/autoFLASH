import os
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin

def get_homeworks(s: requests.Session, lesson_id):
    domain = os.getenv("API_DOMAIN")
    login_url = f"https://{domain}/login"

    # 1. загрузка страницы логина
    login_page = s.get(login_url)
    soup = BeautifulSoup(login_page.text, "html.parser")

    form = soup.find("form")
    if not form:
        raise RuntimeError("Не найдена форма логина")

    # 2. собираем payload
    login_data = {}
    for inp in form.find_all("input"):
        if not inp.get("name"):
            continue
        login_data[inp["name"]] = inp.get("value", "")

    login_data["email"] = os.getenv("API_ACCOUNT_EMAIL")
    login_data["password"] = os.getenv("API_ACCOUNT_PASSWORD")

    action = form.get("action") or "/login"
    if not action.startswith("http"):
        action = urljoin(login_url, action)

    headers = {"User-Agent": "Mozilla/5.0", "Referer": login_url}

    # 3. логинимся
    login_resp = s.post(action, data=login_data, headers=headers)

    # 4. проверяем успешность
    if "login" in login_resp.url or "Ошибка" in login_resp.text:
        raise RuntimeError("Авторизация не удалась")

    # 5. запрос на student_live
    url = f"https://{domain}/student_live/index"
    resp = s.get(
        url,
        params={
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
        },
        headers=headers,
    )

    # ⚡️ выводим диагностику
    print("URL:", resp.url)
    print("Status:", resp.status_code)
    print("Title:", BeautifulSoup(resp.text, "html.parser").title.get_text(strip=True))
    print("Preview:", resp.text[:400], "...\n")

    return resp
