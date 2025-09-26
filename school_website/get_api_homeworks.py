import os
import requests
from bs4 import BeautifulSoup

def get_homeworks(s: requests.Session, lesson_id: str) -> requests.Response:
    """
    Получаем страницу домашки по уроку через переданную сессию.
    """
    # Загружаем страницу логина и берём CSRF токен
    login_page = s.get(f"https://{os.getenv('API_DOMAIN')}/login")
    print("Login page status:", login_page.status_code)
    print("Login page snippet:", login_page.text[:500])
    soup = BeautifulSoup(login_page.text, "html.parser")
    csrf_input = soup.find("input", {"name": "_token"})
    if not csrf_input:
        raise RuntimeError("Не удалось найти CSRF токен на странице логина")
    csrf_token = csrf_input.get("value")

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
