import typing as tp
from datetime import datetime
import pytz


def get_moscow_date() -> datetime.date:
    # Часовой пояс Москвы
    moscow_tz = pytz.timezone("Europe/Moscow")

    # Получаем текущую дату и время в Москве
    current_moscow_time = datetime.now(moscow_tz)

    # Возвращаем только дату
    return current_moscow_time.date()


def sort_by_date(data):
    return sorted(data, key=lambda x: datetime.strptime(x[2], "%d.%m.%Y"))


def filter_dates_by_today(data: tp.List[tp.Tuple[str]]) -> tp.List[str]:
    today = get_moscow_date()

    result = []
    for lesson_id, title, date_str in data:
        # Преобразуем строку с датой в объект даты
        item_date = datetime.strptime(date_str, "%d.%m.%Y").date()

        # Если дата совпадает с сегодняшней, добавляем элемент в результат
        if item_date == today:
            result.append(title)

    return result


def filter_dates_in_range(
        data: tp.List[tp.Tuple[str, str, str]], last_deadline: str
) -> tp.List[tp.Tuple[str, str, str]]:
    # преобразуем last_deadline в дату
    deadline_date = datetime.strptime(last_deadline, "%d.%m.%Y").date() if last_deadline else datetime.min.date()

    result = []
    for lesson_id, title, date_str in data:
        item_date = datetime.strptime(date_str, "%d.%m.%Y").date()
        if item_date < deadline_date:   # убираем проверку на today
            result.append((lesson_id, title, date_str))
    return result
