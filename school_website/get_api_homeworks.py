import os
import requests
from bs4 import BeautifulSoup

def get_homeworks(s: requests.Session, lesson_id: str) -> requests.Response:
    """
    Получаем страницу домашки по уроку через переданную сессию.
    """
    # Загружаем страницу логина и берём CSRF токен из meta
    login_page = s.get(f"https://{os.getenv('API_DOMAIN')}/login")
    soup = BeautifulSoup(login_page.text, "html.parser")

    csrf_meta = soup.find("meta", {"name": "csrf-token"})
    if not csrf_meta:
        raise RuntimeError("Не удалось найти CSRF токен на странице логина")
    csrf_token = csrf_meta.get("content")
    print("CSRF token:", csrf_token)

    # Авторизация
    login_data = {
        "email": os.getenv("API_ACCOUNT_EMAIL"),
        "password": os.getenv("API_ACCOUNT_PASSWORD"),
        "_token": csrf_token,
    }
    login_resp = s.post(f"https://{os.getenv('API_DOMAIN')}/login", data=login_data)
    if "login" in login_resp.url:
        raise RuntimeError("Авторизация не удалась")

    # Получаем страницу с домашкой
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
    )
    return resp
