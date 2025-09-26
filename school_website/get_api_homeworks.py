import os
import requests

def get_homeworks(s: requests.Session, lesson_id: str):
    # НЕ делаем login здесь!
    # Берём страницу домашки напрямую через сессию, которая уже авторизована
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
