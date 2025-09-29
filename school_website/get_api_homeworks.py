import os
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin

def get_homeworks(s: requests.Session, lesson_id):
    login_url = f"https://{os.getenv('API_DOMAIN')}/login"
    login_page = s.get(login_url)
    soup = BeautifulSoup(login_page.text, "html.parser")

    # ищем форму логина
    form = soup.find("form")
    if not form:
        raise RuntimeError("Не найдена форма логина")

    # собираем все input'ы
    login_data = {}
    for inp in form.find_all("input"):
        name = inp.get("name")
        if not name:
            continue
        login_data[name] = inp.get("value", "")

    # перезаписываем email и password
    login_data["email"] = os.getenv("API_ACCOUNT_EMAIL")
    login_data["password"] = os.getenv("API_ACCOUNT_PASSWORD")

    # формируем action
    action = form.get("action") or "/login"
    if not action.startswith("http"):
        action = urljoin(login_url, action)

    # заголовки для имитации браузера
    headers = {
        "User-Agent": "Mozilla/5.0",
        "Referer": login_url,
    }

    # авторизация
    login_resp = s.post(action, data=login_data, headers=headers)
    if "login" in login_resp.url or "Ошибка" in login_resp.text:
        raise RuntimeError("Авторизация не удалась")

    # запрос на страницу с домашками
    resp = s.get(
        f'https://{os.getenv("API_DOMAIN")}/student_live/index',
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
    resp.raise_for_status()
    return resp
