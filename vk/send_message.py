import os

import random
import vk_api
import requests

VK_API_VERSION = '5.101'
VK_DEADLINE_PICTURE = 'vk/img/deadline.jpg'


def connect():
    """Авторизуемся в VK"""

    vk_session = vk_api.VkApi(
        token=os.getenv('VK_API_TOKEN'),
        api_version=VK_API_VERSION
    )
    return vk_session.get_api()


def send_deadline_message(lesson_title: str) -> bool:
    api = connect()

    # Получаем адрес сервера для загрузки картинки
    upload_url = api.photos.getMessagesUploadServer(GROUP_ID=os.getenv('VK_GROUP_ID'), v=VK_API_VERSION)[
        'upload_url']

    while True:
        try:
            # Формируем данные параметров для сохранения картинки на сервере
            request = requests.post(upload_url, files={'photo': open(VK_DEADLINE_PICTURE, "rb")})
            break
        except Exception as error:
            print('At send_message:', error)

    params = {
        'server': request.json()['server'],
        'photo': request.json()['photo'],
        'hash': request.json()['hash'],
        'GROUP_ID': os.getenv('VK_GROUP_ID'),
        'v': VK_API_VERSION
    }

    # Сохраняем картинку на сервере и получаем её идентификатор
    photo_id = api.photos.saveMessagesPhoto(**params)[0]['id']

    # Формируем параметры для отправки картинки в ЛС и отправляем её
    params = {
        'chat_id': '1',  # ID пользователя, которому мы должны отправить картинку
        'random_id': random.randint(1, 2147483647),
        'message': f'@all, сегодня #дедлайн по {lesson_title}',
        'attachment': f"photo-{os.getenv('VK_GROUP_ID')}_{photo_id}",
        'v': VK_API_VERSION
    }

    return api.messages.send(**params)
