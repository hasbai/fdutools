from bs4 import BeautifulSoup

from fudan import Fudan


class Grade(Fudan):
    def get_grade(self, semester_id):
        grade_url = 'https://jwfw.fudan.edu.cn/eams/teach/grade/course/person!search.action'
        r = self.c.get(grade_url, params={'semesterId': semester_id})

        soup = BeautifulSoup(r.text, features='lxml')
        result = []
        for item in soup.tbody.children:
            strings = list(item.stripped_strings)
            result.append(strings[3] + ' ' + strings[6])
        return result

    def get_gpa(self):
        gpa_url = 'https://jwfw.fudan.edu.cn/eams/myActualGpa!search.action'
        r = self.c.get(gpa_url)

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
