import os

import random
import vk_api
import requests


def connect():
    """Авторизуемся в VK"""

    vk_session = vk_api.VkApi(
        token=os.getenv('vk_api_token'),
        api_version=os.getenv('vk_api_version')
    )
    return vk_session.get_api()


def send_deadline_message(lesson_title: str) -> bool:
    api = connect()

    # Получаем адрес сервера для загрузки картинки
    upload_url = api.photos.getMessagesUploadServer(GROUP_ID=os.getenv('vk_group_id'), v=os.getenv('vk_api_version'))['upload_url']

    while True:
        try:
            # Формируем данные параметров для сохранения картинки на сервере
            request = requests.post(upload_url, files={'photo': open(os.getenv('vk_deadline_picture'), "rb")})
            break
        except Exception as error:
            print('At send_message:', error)

    params = {
        'server': request.json()['server'],
        'photo': request.json()['photo'],
        'hash': request.json()['hash'],
        'GROUP_ID': os.getenv('vk_group_id'),
        'v': os.getenv('vk_api_version')
    }

    # Сохраняем картинку на сервере и получаем её идентификатор
    photo_id = api.photos.saveMessagesPhoto(**params)[0]['id']

    # Формируем параметры для отправки картинки в ЛС и отправляем её
    params = {
        'chat_id': '2',  # ID пользователя, которому мы должны отправить картинку
        'random_id': random.randint(1, 2147483647),
        'message': f'@all, сегодня #дедлайн по {lesson_title}',
        'attachment': f"photo-{os.getenv('vk_group_id')}_{photo_id}",
        'v': os.getenv('vk_api_version')
    }

    return api.messages.send(**params)
