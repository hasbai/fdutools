import dbm

import pandas as pd
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
        self.full_grades = None

    def get_full_grades(self):
        if self.full_grades is not None:
            return self.full_grades
        grade_url = 'https://my.fudan.edu.cn/list/bks_xx_cj'
        r = self.c.get(grade_url, follow_redirects=True)
        soup = BeautifulSoup(r.text, features='lxml')
        df = pd.DataFrame(
            data=[tr.stripped_strings for tr in soup.tbody.children],
            columns=['code', 'year', 'semester', 'name', 'credit', 'grade']
        )  # ['课程代码', '学年', '学期', '课程名称', '学分', '最终成绩']
        df.credit = df.credit.astype('float')
        df = df[df.grade != 'P']  # 过滤 P 的课程
        # 转换绩点
        trans = {
            'A': 4.0,
            'A-': 3.7,
            'B+': 3.3,
            'B': 3.0,
            'B-': 2.7,
            'C': 2.4
        }
        point = []
        for i in df['grade']:
            point.append(trans.get(i, 2.0))
        df['point'] = point

        self.full_grades = df
        return df

    def get_grade(self):
        df = self.get_full_grades()
        year, semester = df.year[0], df.semester[0]
        df = df[(df.year == year) & (df.semester == semester)]
        return list(map(lambda i: f'{i[0]}  {i[1]}', zip(df.name, df.grade)))

    def get_gpa(self):
        if not self.jwfw:
            df = self.get_full_grades()
            gpa = sum(df.credit * df.point) / sum(df.credit)
            return f'我的绩点为：{gpa:.2f}\n教务网站不可用，无法查询排名！'

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
        return f'我的绩点为：{gpa:.2f}\n专业排名为：{percentage:.1f}%'


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
    # with Grade(**config.users[0]) as g:
    #     print(g.get_gpa())
