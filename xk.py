import re

import demjson
import prettytable
from bs4 import BeautifulSoup

import config
from fudan import Fudan


class Xk(Fudan):
    def __init__(self, username, password):
        super().__init__(username, password)
        self.login_url = 'https://xk.fudan.edu.cn/xk/login.action'
        self.logout_url = 'https://xk.fudan.edu.cn/xk/logout.action'

        self.profile_id = 0

    def login(self):
        data = {
            'username': self.username,
            'password': self.password,
        }

        r = self.c.post(
            self.login_url,
            data=data,
            allow_redirects=False
        )
        assert r.status_code == 302, '登录失败'

    def get_xk(self):
        xk_url = 'https://xk.fudan.edu.cn/xk/stdElectCourse!defaultPage.action'

        # 获取 profile_id
        r = self.c.get(xk_url)
        soup = BeautifulSoup(r.text, features='lxml')
        tag = soup.find(name='input', attrs={'type': 'hidden'})
        self.profile_id = tag['value']
        data = {tag['name']: tag['value']}
        r = self.c.post(xk_url, data=data)  # 需要先访问选课页面才能获得已选课程
        assert r.status_code == 200, '访问选课页面失败！'

    def show_courses_table(self):
        # 获取已选课程
        query_course_url = 'https://xk.fudan.edu.cn/xk/stdElectCourse!queryLesson.action'
        r = self.c.get(query_course_url, params={'profileId': self.profile_id})
        assert r.status_code == 200, '查询课表失败！'
        text = re.search(r'\[.*]', r.text).group()
        selected_courses = demjson.decode(text)  # dict

        # 生成课表
        array = [[''] * 7 for i in range(14)]
        for course in selected_courses:
            start_unit = course['arrangeInfo'][0]['startUnit']
            end_unit = course['arrangeInfo'][0]['endUnit']
            weekday = course['arrangeInfo'][0]['weekDay']
            for i in range(start_unit - 1, end_unit):
                array[i][weekday - 1] = course['name']

        # 打印课表
        table = prettytable.PrettyTable(['星期一', '星期二', '星期三', '星期四', '星期五', '星期六', '星期日'])
        for row in array:
            table.add_row(row)
        print(table)

    def query_course(self, course_no):
        def search_course_id(_courses, _course_no):
            for course in _courses:
                if course['no'] == _course_no:
                    return course['id']
            raise Exception('没有找到这门课！{}'.format(_course_no))

        query_course_url = 'https://xk.fudan.edu.cn/xk/stdElectCourse!queryLesson.action'
        r = self.c.post(
            query_course_url,
            params={'profileId': self.profile_id},
            data={'lessonNo': course_no, 'courseCode': '', 'courseName': ''}
        )
        assert r.status_code == 200, '查询课程失败！'
        text = re.search(r'\[.*]', r.text).group()
        courses = demjson.decode(text)  # dict
        return search_course_id(courses, course_no)

    def operate_course(self, course_id, mode='select'):
        operate_course_url = 'https://xk.fudan.edu.cn/xk/stdElectCourse!batchOperator.action'
        data = {'optype': 'true', 'operator0': '{}:true:0'.format(course_id)} \
            if mode == 'select' else \
            {'optype': 'false', 'operator0': '{}:false'.format(course_id)}

        r = self.c.post(
            operate_course_url,
            params={'profileId': self.profile_id},
            data=data
        )
        soup = BeautifulSoup(r.text, features='lxml')
        message = re.sub(r'\s', '', soup.body.get_text())
        print(message)

        assertion_message = '选课失败！' if mode == 'select' else '退课失败！'
        assert '成功' in message, assertion_message


if __name__ == '__main__':
    c = Xk(config.username, config.password)
    try:
        c.login()
        c.get_xk()
        # _course_id = c.query_course('ECON130223.01')
        # c.operate_course(_course_id, 'select')
        c.show_courses_table()

    except Exception as e:
        # traceback.print_exc()
        print('[E] {}'.format(e))
    finally:
        c.close()
