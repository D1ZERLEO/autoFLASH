from vk.config import base_request_params, GROUP_ID
import paths

import random
import vk_api
import requests


def connect():
    """Авторизуемся в VK"""

    vk_session = vk_api.VkApi(
        token=base_request_params['access_token'],
        api_version=base_request_params['v']
    )
    return vk_session.get_api()


def send_deadline_message(lesson_title: str) -> bool:
    api = connect()

    # Получаем адрес сервера для загрузки картинки
    upload_url = api.photos.getMessagesUploadServer(GROUP_ID=GROUP_ID, v=base_request_params['v'])['upload_url']

    while True:
        try:
            # Формируем данные параметров для сохранения картинки на сервере
            request = requests.post(upload_url, files={'photo': open(paths.DEADLINE_PICTURE, "rb")})
            break
        except Exception as error:
            print('At send_message:', error)

    params = {
        'server': request.json()['server'],
        'photo': request.json()['photo'],
        'hash': request.json()['hash'],
        'GROUP_ID': GROUP_ID,
        'v': base_request_params['v']
    }

    # Сохраняем картинку на сервере и получаем её идентификатор
    photo_id = api.photos.saveMessagesPhoto(**params)[0]['id']

    # Формируем параметры для отправки картинки в ЛС и отправляем её
    params = {
        'chat_id': '2',  # ID пользователя, которому мы должны отправить картинку
        'random_id': random.randint(1, 2147483647),
        'message': f'@all, сегодня #дедлайн по {lesson_title}',
        'attachment': f'photo-{GROUP_ID}_{photo_id}',
        'v': base_request_params['v']
    }

    return api.messages.send(**params)
