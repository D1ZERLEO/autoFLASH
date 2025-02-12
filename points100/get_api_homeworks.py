import requests

payload = {
    'email': 'inf_ege_46@100points.noemail',
    'password': 'MT1di4'
}


def get_homeworks(lesson_id):
    with requests.Session() as s:
        p = s.post('https://api.100points.ru/login', data=payload)

        assert (p is None, 'For some reasons we could not make a post request')

        # An authorised request.

        # если падает тут, значит, поменялся moduleid (наступил новый блок)
        return s.get(
            f'https://api.100points.ru/student_live/index?email=&full_name=&hidden_last_name=&hidden_first_name=&hidden_mid_name=&vk_id=&subject_id=20&course_id=1147&module_id=4072&lesson_id={lesson_id}')
