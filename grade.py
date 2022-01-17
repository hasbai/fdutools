import dbm

from bs4 import BeautifulSoup

import config
from fudan import Fudan
from utils.mail import send_email


class Grade(Fudan):
    def __init__(self, username, password, **kwargs):
        super().__init__(username, password)
        self.semester_id = kwargs.get('semester_id', config.semester_id)
        try:
            self.c.get('https://jwfw.fudan.edu.cn')
            self.jwfw = True
        except:
            self.jwfw = False

    def get_grade(self):
        result = []

        if self.jwfw:  # 教务网站通道
            grade_url = 'https://jwfw.fudan.edu.cn/eams/teach/grade/course/person!search.action'
            r = self.c.get(grade_url, params={'semesterId': self.semester_id}, follow_redirects=True)
            soup = BeautifulSoup(r.text, features='lxml')
            for tr in soup.tbody.children:
                li = list(tr.stripped_strings)
                if len(li) > 6:
                    result.append(li[3] + ' ' + li[6])

        else:  # my.fudan.edu.cn 通道
            grade_url = 'https://my.fudan.edu.cn/list/bks_xx_cj'
            r = self.c.get(grade_url, follow_redirects=True)
            soup = BeautifulSoup(r.text, features='lxml')
            year, semester = None, None
            for tr in soup.tbody.children:
                li = list(tr.stripped_strings)
                if year is None:
                    year = li[1]
                    semester = li[2]
                if year != li[1] or semester != li[2]:
                    break
                result.append(li[3] + ' ' + li[5])

        return result

    def get_gpa(self):
        if not self.jwfw:
            return '教务网站不可用，无法查询绩点！'

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
        grades = grade.get_grade()
        gpa_report = grade.get_gpa()

    print(username)
    [print(grade) for grade in grades]
    print(gpa_report)

    if not is_send_email:
        return
    key = f'{username}-grade-nums'
    with dbm.open('data/grade.db', 'c') as db:
        grade_nums = int(db.get(key, 0))
        if grade_nums != len(grades):
            db[key] = str(len(grades))
            content = f'{username}\r\n' + '\r\n'.join(grades) + f'\r\n{gpa_report}'
            send_email('考试成绩快报', content, email)


if __name__ == '__main__':
    grade_report(**config.users[0])
