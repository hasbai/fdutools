import json

from bs4 import BeautifulSoup

import config
from fudan import Fudan
from utils.email import send_email


class Grade(Fudan):
    def __init__(self, username, password, **kwargs):
        super().__init__(username, password)
        self.logout_service = 'https://jwfw.fudan.edu.cn/eams/login.action'

    def get_grade(self, semester_id):
        grade_url = 'https://jwfw.fudan.edu.cn/eams/teach/grade/course/person!search.action'
        r = self.c.get(grade_url, params={'semesterId': semester_id}, follow_redirects=True)

        soup = BeautifulSoup(r.text, features='lxml')
        result = []
        for item in soup.tbody.children:
            strings = list(item.stripped_strings)
            if len(strings) > 6:
                result.append(strings[3] + ' ' + strings[6])
        return result

    def get_gpa(self):
        gpa_url = 'https://jwfw.fudan.edu.cn/eams/myActualGpa!search.action'
        r = self.c.get(gpa_url, follow_redirects=True)

        soup = BeautifulSoup(r.text, features='lxml')
        gpas = []
        major = ''
        gpa = ''

        for item in soup.tbody.children:
            strings = list(item.stripped_strings)
            if strings[0][0] != '*':
                major = strings[3]
                gpa = strings[5]
                break

        for item in soup.tbody.children:
            strings = list(item.stripped_strings)
            if strings[3] == major:
                gpas.append(strings[5])

        gpas.sort()
        gpas.reverse()
        percentage = (gpas.index(gpa) + 1) / len(gpas) * 100
        return '我的绩点为：{}\n专业排名为：{:.1f}%'.format(gpa, percentage)


def grade_report(username, password, email, is_send_email=True, **kwargs):
    with Grade(username, password) as grade:
        grades = grade.get_grade(config.semester_id)
        gpa_report = grade.get_gpa()

    print(username)
    [print(grade) for grade in grades]
    print(gpa_report)

    if not is_send_email:
        return

    try:
        with open('result.json', 'r') as file:
            grade_nums = json.load(file)
    except FileNotFoundError:
        pass
        grade_nums = {}

    if not grade_nums.get(username):
        grade_nums[username] = 0

    if grade_nums[username] != len(grades):
        grade_nums[username] = len(grades)
        content = username + '\r\n' + '\r\n'.join(grades) + gpa_report
        send_email('考试成绩快报', content, [email])

    with open('result.json', 'w') as file:
        json.dump(grade_nums, file)


if __name__ == '__main__':
    grade_report(**config.users[0])
