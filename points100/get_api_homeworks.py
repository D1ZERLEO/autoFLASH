import os

import requests


def get_homeworks(lesson_id):
    """
    !!! Вероятно, наступил новый блок, поэтому в github.secrets нужно
    поменять переменную MODULE_ID на айдишник нового модуля. Для этого
    вручную зайдите на сайт апи, посмотрите журнал по домашке из нового блока.
    В адресной строке изучите ссылку. Число в параметре &module_id= будет тем, что вам нужно.
    """

    with requests.Session() as s:
        s.post(f"https://{os.getenv('api_domain')}/login", data={
            'email': os.getenv('api_account_email'),
            'password': os.getenv('api_account_password')
        })

        return s.get(
            f'https://{os.getenv("api_domain")}/student_live/index?email=&full_name=&hidden_last_name=&hidden_first_name=&hidden_mid_name=&vk_id=&subject_id=20&course_id=1147&module_id={os.getenv("module_id")}&lesson_id={lesson_id}')
